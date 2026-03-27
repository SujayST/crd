from django.urls import path
from .views import CRDDocIngestView, CustomerExcelIngestView, SMEQuestionsIngestView, HealthView

urlpatterns = [
    path("ingest/crd-docs/", CRDDocIngestView.as_view(), name="ingest-crd-docs"), #First endpoint to ingest CRD documents
    path("ingest/customer-excel/", CustomerExcelIngestView.as_view(), name="ingest-customer-excel"), #SME responses ingest endpoint
    path("ingest/sme-questions/", SMEQuestionsIngestView.as_view(), name="ingest-sme-questions"), #SME additional questions ingest endpoint
    path("health/", HealthView.as_view(), name="health"), #Health check endpoint
]
