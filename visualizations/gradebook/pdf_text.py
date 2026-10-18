"""Extract a bounded syllabus in a separate process; no files or network access."""
from io import BytesIO
import logging
import sys

from pypdf import PdfReader

if __name__ == '__main__':
    if sys.platform != 'win32':
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
        if sys.platform == 'linux':
            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    logging.getLogger('pypdf').disabled = True
    reader = PdfReader(BytesIO(sys.stdin.buffer.read(5 * 1024 * 1024 + 1)))
    if reader.is_encrypted or len(reader.pages) > 30:
        sys.exit(1)
    output = []
    for page in reader.pages:
        stream = page.get_contents()
        if stream is not None and len(stream.get_data()) > 5 * 1024 * 1024:
            sys.exit(1)
        output.append(page.extract_text() or '')
    text = '\n'.join(output)
    if len(text) > 60000:
        sys.exit(1)
    print(text)
