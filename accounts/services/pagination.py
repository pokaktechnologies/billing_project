from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


def api_response(status="1", message="Success", data=None):
    return Response({
        "Status": status,
        "message": message,
        "Data": data
    })


class OptionalPagination(PageNumberPagination):

    page_size_query_param = "page_size"

    def get_page_size(self, request):
        page_size = request.query_params.get("page_size")

        if not page_size:
            return None

        try:
            return int(page_size)
        except ValueError:
            return None

    def get_paginated_response(self, data):
        return Response({
            "Status": "1",
            "message": "Success",
            "count": self.page.paginator.count,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "Data": data
        })


def paginate_response(queryset, request, serializer_class, **serializer_kwargs):

    paginator = OptionalPagination()
    page = paginator.paginate_queryset(queryset, request)

    if page is not None:
        serializer = serializer_class(page, many=True, **serializer_kwargs)
        return paginator.get_paginated_response(serializer.data)

    serializer = serializer_class(queryset, many=True, **serializer_kwargs)
    return api_response(data=serializer.data)