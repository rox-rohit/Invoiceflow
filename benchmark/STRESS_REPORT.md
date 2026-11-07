# InvoiceFlow large-batch stress test

These are synthetic stress fixtures for stability and throughput only. They are not extraction-accuracy evidence.

## Environment

- Windows 11
- Python 3.15.0
- PyMuPDF 1.28.2
- Two bounded worker threads
- 2,000 generated text PDFs

## Results

| Input | PDFs | Errors | Elapsed | Throughput | Peak Python working set |
|---|---:|---:|---:|---:|---:|
| Directory | 2,000 | 0 | 58.935 s | 33.94 PDFs/s | 273 MB |
| ZIP archive | 2,000 | 0 | 71.453 s | 27.99 PDFs/s | 272.8 MB |

The final post-job-state rerun also completed both directory and ZIP processes with exit code 0 and peak working sets of 273 MB and 272.8 MB respectively. The ZIP run is streamed one PDF at a time; PDFs are not extracted into a permanent batch directory.

The test does not establish real-world invoice accuracy. It verifies bounded memory behavior, failure isolation and completion at the required 2,000-document scale.
