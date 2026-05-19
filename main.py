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