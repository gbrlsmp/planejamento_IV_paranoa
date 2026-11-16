"""Recortes HTML por estrutura, preservando literalmente os outros painéis."""
from html.parser import HTMLParser


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.offsets = [0]
        for line in text.splitlines(keepends=True):
            self.offsets.append(self.offsets[-1]+len(line))
        self.stack = []
        self.elements = []
        self.feed(text)

    def position(self):
        line, col = self.getpos()
        return self.offsets[line-1]+col

    def handle_starttag(self, tag, attrs):
        if tag not in ('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'):
            self.stack.append((tag, dict(attrs), self.position()))

    def handle_endtag(self, tag):
        if not self.stack:
            return
        if self.stack[-1][0] != tag:
            raise ValueError(f'HTML mal aninhado: {tag}, {self.stack[-1]}')
        kind, attrs, start = self.stack.pop()
        end = self.text.index('>',self.position())+1
        self.elements.append(dict(tag=kind, attrs=attrs, start=start, end=end))

    def by_id(self, identifier):
        found = [e for e in self.elements if e['attrs'].get('id') == identifier]
        if len(found) != 1:
            raise ValueError((identifier,len(found)))
        return found[0]

    def fragment(self, identifier):
        e = self.by_id(identifier)
        return self.text[e['start']:e['end']]
