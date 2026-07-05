from rest_framework.routers import DefaultRouter
from .views import EstudianteMatriculaViewSet

router = DefaultRouter()
router.register(r'estudiantes', EstudianteMatriculaViewSet, basename='estudiantes')

urlpatterns = router.urls
