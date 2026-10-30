from rest_framework.pagination import PageNumberPagination


class ReportPagination(PageNumberPagination):
    page_size_query_param = 'page_size'

    def get_page_size(self, request):
        page_size = request.query_params.get('page_size')
        if page_size is None:
            return None
        return int(page_size)


class Pagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50
