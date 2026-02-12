from rest_framework.pagination import PageNumberPagination

class OptionalPagination(PageNumberPagination):
    """
    Pagination class that only paginates if 'page', 'page_size', or 'size' 
    is present in the query parameters.
    """
    page_size_query_param = 'page_size'
    
    def paginate_queryset(self, queryset, request, view=None):
        # Look for custom 'size' param as well
        size = request.query_params.get('size')
        if size:
            self.page_size = int(size)
            
        # Check if any pagination-related param is present
        if not any(param in request.query_params for param in ['page', 'page_size', 'size']):
            return None
        
        return super().paginate_queryset(queryset, request, view)
