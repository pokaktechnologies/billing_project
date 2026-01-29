from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from ..models import Account
from ..serializers.accounts import AccountSerializer


class AccountListCreateAPIView(generics.ListCreateAPIView):
    queryset = Account.objects.all().order_by('-created_at')
    serializer_class = AccountSerializer


class AccountRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Account.objects.all()
    serializer_class = AccountSerializer


class GenerateAccountNumberView(APIView):
    """
    Generate account numbers for the Chart of Accounts.
    
    Level 1 (Type): Display-only, fixed number per type
        GET /generate-account-number/?type=asset
        Returns: {"account_number": "10000", "level": 1, "is_fixed": true}
    
    Level 2 (Parent): Generates NEXT available parent number
        GET /generate-account-number/?type=asset&level=parent
        Returns: {"next_number": "1.1000", "level": 2}
    
    Level 3 (Child): Generates NEXT available child number
        GET /generate-account-number/?parent_account=5
        Returns: {"next_number": "1.10001", "level": 3}
    """
    
    def get(self, request):
        parent_account_id = request.query_params.get('parent_account')
        account_type = request.query_params.get('type')
        level = request.query_params.get('level', '').lower()
        
        # Case 1: Generate NEXT child number under a parent
        if parent_account_id:
            try:
                parent = Account.objects.get(pk=parent_account_id)
            except Account.DoesNotExist:
                return Response(
                    {"error": "Parent account not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Check parent depth
            # DB Depth 1 = Level 2 (Parent)
            # DB Depth 2 = Level 3 (Child)
            # Cannot add child to DB Depth 2 (Level 3) accounts
            parent_depth = parent.get_depth()
            if parent_depth >= 2:
                return Response(
                    {"error": "Cannot create child under this account. Maximum depth is 3 levels (Level 3 accounts cannot have children)."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            next_number = self._get_next_child_number(parent)
            return Response({
                "next_number": next_number,
                "level": parent_depth + 2,  # Depth 1 -> Level 3
                "parent_account": parent_account_id,
                "parent_number": parent.account_number,
                "type": parent.type
            })
        
        # Case 2: Generate type-level (display) or parent-level (next) number
        if not account_type:
            return Response(
                {"error": "Either 'type' or 'parent_account' parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate account type
        valid_types = [t[0] for t in Account.ACCOUNT_TYPES]
        if account_type not in valid_types:
            return Response(
                {"error": f"Invalid type. Must be one of: {', '.join(valid_types)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        prefix = Account.TYPE_PREFIX_MAP.get(account_type)
        
        if level == 'parent':
            # Generate NEXT Level 2 (parent) number: X.Y000
            next_number = self._get_next_parent_number(account_type, prefix)
            return Response({
                "next_number": next_number,
                "level": 2,
                "type": account_type
            })
        else:
            # Level 1 is DISPLAY-ONLY (fixed number per type)
            type_number = self._get_type_number(account_type, prefix)
            return Response({
                "account_number": type_number,
                "level": 1,
                "type": account_type,
                "is_fixed": True,
                "message": "Type-level account number is fixed per type (one per type)"
            })
    
    def _get_type_number(self, account_type, prefix):
        """
        Get the type-level account number (X0000).
        This is a FIXED number per type - only one exists per account type.
        Format: 10000, 20000, 30000, etc. (no dot for type level)
        """
        return f"{prefix}0000"
    
    def _get_next_parent_number(self, account_type, prefix):
        """
        Generate next parent-level account number (X.Y000).
        Format: 1.1000, 1.2000, 1.3000, etc.
        """
        # Find all parent-level accounts (X.Y000)
        existing = Account.objects.filter(
            type=account_type,
            account_number__startswith=f"{prefix}.",
            account_number__endswith="000"
        ).order_by('-account_number')
        
        if existing.exists():
            last_number = existing.first().account_number
            try:
                parts = last_number.split('.')
                # Extract Y from X.Y000
                current_sub = int(parts[1][0])
                next_sub = current_sub + 1
                return f"{prefix}.{next_sub}000"
            except (ValueError, IndexError):
                pass
        
        # First parent account
        return f"{prefix}.1000"
    
    def _get_next_child_number(self, parent):
        """
        Generate next child account number under a parent.
        
        PRIORITY: Check existing children first and follow their pattern.
        If no children exist, determine pattern based on parent's number format.
        """
        parent_num = parent.account_number
        parent_depth = parent.get_depth()
        
        # FIRST: Check if parent already has children - follow their pattern
        children = Account.objects.filter(
            parent_account=parent
        ).order_by('-account_number')
        
        if children.exists():
            last_child = children.first().account_number
            try:
                parts = last_child.split('.')
                if len(parts) == 2:
                    # Format: X.YYYYY -> increment the number after dot
                    current_num = int(parts[1])
                    next_num = current_num + 1
                    return f"{parts[0]}.{next_num}"
                else:
                    # No dot in child number, just increment
                    current_num = int(last_child)
                    return str(current_num + 1)
            except (ValueError, IndexError):
                pass
        
        # NO CHILDREN: Determine pattern from parent's number format
        # NO CHILDREN: Determine pattern from parent's number format
        if '.' in parent_num:
            # Parent has format X.YYYY (e.g., 1.1000)
            # Children increment: 1.1000 -> 1.1001
            try:
                parts = parent_num.split('.')
                parent_sub = int(parts[1])
                return f"{parts[0]}.{parent_sub + 1}"
            except (ValueError, IndexError):
                # Fallback if parsing fails
                return f"{parent_num}1"
        else:
            # Parent has format X0000 (e.g., 10000)
            # Children are X.Y000 format
            prefix = parent_num[0]
            return self._get_next_parent_number(parent.type, prefix)


