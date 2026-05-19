# GCP Dataflow Flex Template Setup with Cross-Project Access

## Overview

This document explains the setup and execution flow for a custom Google Cloud Dataflow Flex Template deployment using multiple GCP projects with dedicated runtime service accounts and cross-project access.

The setup uses:

| Project | Purpose |
|---|---|
| `shared-resources` | Artifact Registry for Flex Template container images |
| `sample-project` | Dataflow runtime project |
| `gcs-project` | Destination Cloud Storage project |

The implementation is divided into two main sections:

1. CI/CD pipeline flow for building and publishing Flex Template images
2. Runtime Dataflow execution and service account permissions

---

# Architecture Overview

```text
GitLab Repository
    ->
GitLab CI/CD
    ->
Build Docker Image
    ->
Push Image to Artifact Registry
    ->
Create Flex Template JSON
    ->
Upload Template JSON to GCS
    ->
Run Dataflow Job
    ->
Worker VMs Execute Pipeline
    ->
Output Written to Destination Bucket
```

---

# 1. CI/CD Flow – Build and Push Flex Template Image

## Objective

This flow is responsible for:

- Building the custom Dataflow Flex Template container image
- Pushing the image to Artifact Registry
- Creating/updating the Flex Template specification JSON
- Uploading the template JSON to Cloud Storage

This flow is expected to run through GitLab CI/CD.

---

# Artifact Registry Setup

Artifact Registry is hosted in:

```text
shared-resources
```

Example repository:

```text
asia-south1-docker.pkg.dev/shared-resources/dataflow-images
```

---

# Example Project Structure

```text
dataflow-flex/
 ├── main.py
 ├── requirements.txt
 ├── Dockerfile
 ├── metadata.json
 └── dummy-flex.json
```

---

# Dockerfile

The Flex Template container uses the Google Dataflow Python launcher base image.

```dockerfile
FROM gcr.io/dataflow-templates-base/python3-template-launcher-base

WORKDIR /template

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . /template

ENV FLEX_TEMPLATE_PYTHON_PY_FILE="/template/main.py"
ENV FLEX_TEMPLATE_PYTHON_REQUIREMENTS_FILE="/template/requirements.txt"
```

---

# Example Beam Pipeline

## `main.py`

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from datetime import datetime

class CreateDummyData(beam.DoFn):
    def process(self, element):
        yield f"Dummy row generated at {datetime.utcnow()}"

def run():
    options = PipelineOptions(
        save_main_session=True,
        streaming=False
    )

    with beam.Pipeline(options=options) as p:
        (
            p
            | "Start" >> beam.Create([1])
            | "GenerateData" >> beam.ParDo(CreateDummyData())
            | "WriteToGCS" >> beam.io.WriteToText(
                "gs://gcs-project-output/output/data",
                file_name_suffix=".txt"
            )
        )

if __name__ == "__main__":
    run()
```

---

# Requirements File

## `requirements.txt`

```txt
apache-beam[gcp]==2.54.0
```

---

# Template Metadata

## `metadata.json`

```json
{
  "name": "dummy-flex-template",
  "description": "Dummy Dataflow Flex Template"
}
```

---

# Flex Template Specification JSON

## `dummy-flex.json`

```json
{
  "image": "asia-south1-docker.pkg.dev/shared-resources/dataflow-images/dummy-flex:latest",
  "sdkInfo": {
    "language": "PYTHON"
  },
  "metadata": {
    "name": "dummy-flex-template",
    "description": "Dummy Dataflow Flex Template"
  }
}
```

---

# Build and Push Container Image

The CI/CD pipeline builds and pushes the image to Artifact Registry.

Example command:

```bash
gcloud builds submit \
  --tag asia-south1-docker.pkg.dev/shared-resources/dataflow-images/dummy-flex:latest \
  --project=shared-resources
```

---

# Upload Template JSON

```bash
gsutil cp dummy-flex.json \
gs://sample-project-dataflow-templates/templates/
```

---

# Suggested CI/CD Responsibilities

The CI/CD pipeline is responsible for:

| Responsibility | Description |
|---|---|
| Build image | Build Flex Template Docker image |
| Push image | Push image to Artifact Registry |
| Template creation | Create/update Flex Template JSON |
| Upload template | Upload template JSON to GCS |
| Versioning | Tagging images and templates |

---

# Recommended CI/CD Service Account Permissions

The CI/CD service account should have:

| Project | Role |
|---|---|
| `shared-resources` | Artifact Registry Writer |
| `sample-project` | Storage Admin (template bucket) |
| `sample-project` | Dataflow Admin (optional if validating templates) |

---

# 2. Dataflow Runtime Execution and Service Account Configuration

## Objective

This section covers:

- Running the Dataflow Flex Template
- Runtime service account configuration
- Cross-project bucket access
- Required IAM permissions

The actual Dataflow execution can be triggered manually or through orchestration tools.

For this documentation, the execution is assumed to be triggered manually using the `gcloud` command.

---

# Runtime Architecture

```text
Dataflow Job (sample-project)
    ->
Worker VMs Created
    ->
Workers Pull Container Image
    ->
Workers Access Source/Destination Buckets
    ->
Workers Execute Beam Pipeline
```

---

# Dedicated Runtime Service Account

A single dedicated runtime service account is used for:

- Dataflow worker execution
- Compute Engine VM identity

Example:

```text
dataflow-worker-sa@sample-project.iam.gserviceaccount.com
```

This service account becomes the runtime identity attached to the worker VMs created by Dataflow.

---

# Why a Dedicated Runtime Service Account

Using a dedicated runtime service account provides:

- Runtime isolation
- Cross-project access control
- Better IAM governance
- Removal of dependency on default Compute Engine service accounts

This is the recommended production approach.

---

# Create the Runtime Service Account

```bash
gcloud iam service-accounts create dataflow-worker-sa \
  --display-name="Dedicated Dataflow Worker SA" \
  --project=sample-project
```

---

# Runtime Permissions – sample-project

The worker service account requires the following permissions in the Dataflow runtime project.

---

## Dataflow Worker Role

Required for Dataflow worker execution.

```bash
gcloud projects add-iam-policy-binding sample-project \
  --member="serviceAccount:dataflow-worker-sa@sample-project.iam.gserviceaccount.com" \
  --role="roles/dataflow.worker"
```

---

## Storage Access for Temp/Staging Buckets

Required for:

- temp files
- staging files
- shuffle data
- intermediate processing

```bash
gcloud projects add-iam-policy-binding sample-project \
  --member="serviceAccount:dataflow-worker-sa@sample-project.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

---

## Compute Viewer Access

Required internally by Dataflow for Compute Engine resource visibility.

```bash
gcloud projects add-iam-policy-binding sample-project \
  --member="serviceAccount:dataflow-worker-sa@sample-project.iam.gserviceaccount.com" \
  --role="roles/compute.viewer"
```

---

# Runtime Permissions – Artifact Registry Project

The worker service account must pull the Flex Template container image from Artifact Registry.

Project:

```text
shared-resources
```

Required permission:

```bash
gcloud projects add-iam-policy-binding shared-resources \
  --member="serviceAccount:dataflow-worker-sa@sample-project.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

---

# Runtime Permissions – Destination Bucket Project

The worker service account must be able to:

- read bucket metadata
- create output files
- manage objects

Project:

```text
gcs-project
```

Bucket:

```text
gs://gcs-project-output
```

---

# Required Bucket Permissions

## Object-Level Permissions

Required for writing files.

```bash
gsutil iam ch \
serviceAccount:dataflow-worker-sa@sample-project.iam.gserviceaccount.com:objectAdmin \
gs://gcs-project-output
```

---

## Bucket Metadata Read Permission

Required because Apache Beam validates the bucket before writing.

```bash
gsutil iam ch \
serviceAccount:dataflow-worker-sa@sample-project.iam.gserviceaccount.com:legacyBucketReader \
gs://gcs-project-output
```

---

# Important Note on Bucket Permissions

Even if object write permissions are granted, Dataflow may still fail unless the worker service account can read bucket metadata.

Typical error:

```text
storage.buckets.get permission denied
```

This occurs because Beam internally validates bucket existence before writing output.

---

# Running the Dataflow Flex Template

Example execution command:

```bash
gcloud dataflow flex-template run "dummy-flex-job-001" \
  --template-file-gcs-location gs://sample-project-dataflow-templates/templates/dummy-flex.json \
  --region asia-south1 \
  --service-account-email dataflow-worker-sa@sample-project.iam.gserviceaccount.com \
  --staging-location gs://sample-project-dataflow-temp/staging \
  --temp-location gs://sample-project-dataflow-temp/temp \
  --project=sample-project
```

---

# Runtime Flow

At runtime:

1. Dataflow launches worker VMs
2. Worker VMs use the dedicated runtime service account
3. Workers pull the container image from Artifact Registry
4. Workers access staging/temp buckets
5. Workers execute the Beam pipeline
6. Workers write output to destination buckets

---

# Source and Destination Configuration

The source and destination systems can be configured based on application requirements.

Examples include:

| Type | Example |
|---|---|
| Source | Cloud Storage |
| Source | BigQuery |
| Source | Pub/Sub |
| Destination | Cloud Storage |
| Destination | BigQuery |
| Destination | Databases |

The same runtime service account model can be extended by granting the required IAM permissions for the respective source and destination systems.

---

# Recommended Bucket Separation

Recommended bucket layout:

| Bucket Purpose | Example |
|---|---|
| Templates | `sample-project-dataflow-templates` |
| Temp | `sample-project-dataflow-temp` |
| Staging | `sample-project-dataflow-staging` |
| Output | `gcs-project-output` |

This improves operational isolation and debugging.

---

# Common Failure Scenarios

| Issue | Cause |
|---|---|
| Workers fail to start | Missing Artifact Registry access |
| Permission denied writing output | Missing bucket IAM |
| `storage.buckets.get` denied | Missing bucket metadata read permission |
| Worker pool startup failure | Quota/subnet/stockout issues |
| Flex Template launch failure | Incorrect launcher configuration |

---

# Verification

## Verify Worker Service Account

Go to:

```text
Compute Engine -> VM Instances
```

Open a Dataflow worker VM and verify:

```text
Service Account:
dataflow-worker-sa@sample-project.iam.gserviceaccount.com
```

---

# Verify Output Files

List generated files:

```bash
gsutil ls gs://gcs-project-output/output/
```

Read generated files:

```bash
gsutil cat gs://gcs-project-output/output/*.txt
```

---

# Summary

This setup provides:

- Cross-project Dataflow execution
- Dedicated runtime identity
- Artifact Registry integration
- Flexible source/destination configuration
- Runtime isolation using a dedicated worker service account
- CI/CD-driven Flex Template image management

The same architecture can be extended further for:

- orchestration platforms
- production CI/CD
- custom networking
- VPC isolation
- enterprise IAM governance