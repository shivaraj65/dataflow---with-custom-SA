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
build and Upload Template JSON to GCS
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

## reference link for dockerfile

## reference link for CI/CD.

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

# Permissions for the Dedicated SA


## Create the Runtime Service Account

```bash
gcloud iam service-accounts create dataflow-worker-sa \
  --display-name="Dedicated Dataflow Worker SA" \
  --project=sample-project
```

---

The following permissiosn are required for the SA:

### sample-project permissions

- Artifact Registry Reader
- Compute Viewer
- Dataflow Worker
- Storage Object Admin

### shared-resources - [ artifacts registry project ]

- Artifact Registry Reader

### gcs-project - [ permissions provided on bucket level ]

- storage legacy bucket reader
- storage object admin 

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

# Common Failure Scenarios

| Issue | Cause |
|---|---|
| Workers fail to start | Missing Artifact Registry access |
| Permission denied writing output | Missing bucket IAM |
| `storage.buckets.get` denied | Missing bucket metadata read permission |
| Worker pool startup failure | Quota/subnet/stockout issues |
| Flex Template launch failure | Incorrect launcher configuration |
