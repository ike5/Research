from .models import Category


def sidebar_context(request):
    return {
        "all_categories": Category.objects.order_by("name"),
    }
