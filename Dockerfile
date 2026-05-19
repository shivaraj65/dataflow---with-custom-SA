FROM gcr.io/dataflow-templates-base/python3-template-launcher-base

WORKDIR /template

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py .

ENV FLEX_TEMPLATE_PYTHON_PY_FILE="/template/main.py"
ENV FLEX_TEMPLATE_PYTHON_REQUIREMENTS_FILE="/template/requirements.txt"