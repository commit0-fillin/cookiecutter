"""Jinja2 extensions."""
import json
import string
import uuid
from secrets import choice
import arrow
from jinja2 import nodes
from jinja2.ext import Extension
from slugify import slugify as pyslugify

class JsonifyExtension(Extension):
    """Jinja2 extension to convert a Python object to JSON."""

    def __init__(self, environment):
        """Initialize the extension with the given environment."""
        super().__init__(environment)

        def jsonify(obj):
            return json.dumps(obj, sort_keys=True, indent=4)
        environment.filters['jsonify'] = jsonify

class RandomStringExtension(Extension):
    """Jinja2 extension to create a random string."""

    def __init__(self, environment):
        """Jinja2 Extension Constructor."""
        super().__init__(environment)

        def random_ascii_string(length, punctuation=False):
            if punctuation:
                corpus = ''.join((string.ascii_letters, string.punctuation))
            else:
                corpus = string.ascii_letters
            return ''.join((choice(corpus) for _ in range(length)))
        environment.globals.update(random_ascii_string=random_ascii_string)

class SlugifyExtension(Extension):
    """Jinja2 Extension to slugify string."""

    def __init__(self, environment):
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        def slugify(value, **kwargs):
            """Slugifies the value."""
            return pyslugify(value, **kwargs)
        environment.filters['slugify'] = slugify

class UUIDExtension(Extension):
    """Jinja2 Extension to generate uuid4 string."""

    def __init__(self, environment):
        """Jinja2 Extension constructor."""
        super().__init__(environment)

        def uuid4():
            """Generate UUID4."""
            return str(uuid.uuid4())
        environment.globals.update(uuid4=uuid4)

class TimeExtension(Extension):
    """Jinja2 Extension for dates and times."""
    tags = {'now'}

    def __init__(self, environment):
        """Jinja2 Extension constructor."""
        super().__init__(environment)
        environment.extend(datetime_format='%Y-%m-%d')

    def parse(self, parser):
        """Parse datetime template and add datetime value."""
        lineno = next(parser.stream).lineno

        # Parse any arguments passed to the tag
        args = [parser.parse_expression()]
        
        # If there are no arguments, use the default format
        if parser.stream.current.type != 'block_end':
            parser.fail('Expected end of block', parser.stream.current.lineno)

        # Create a call to arrow.now().format() with the datetime format
        call = self.call_method(
            '_render',
            [nodes.ContextReference()],
            lineno=lineno
        )

        return nodes.Output([call], lineno=lineno)

    def _render(self, context):
        """Render the current date and time."""
        datetime_format = context.environment.datetime_format
        return arrow.now().format(datetime_format)
