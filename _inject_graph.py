"""
Inject graph.json data directly into static/graph.html
so it works without needing to fetch from a server.

Uses regex replacement to handle both initial (null) and existing data states.
Runs idempotently — safe to execute multiple times.
"""
import json
import re

with open('data/graph.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('static/graph.html', 'r', encoding='utf-8') as f:
    html = f.read()

data_json = json.dumps(data)

# Use regex to find and replace the INLINE_GRAPH_DATA assignment
# Use a lambda to avoid escape-sequence interpretation in replacement string
pattern = r'const\s+INLINE_GRAPH_DATA\s*=\s*[^;]+;'
new_html, count = re.subn(
    pattern,
    lambda m: f'const INLINE_GRAPH_DATA = {data_json};',
    html,
    count=1
)

if count == 0:
    print("WARNING: Could not find INLINE_GRAPH_DATA assignment. Appending fallback.")
    new_html = html.replace(
        '</script>',
        f'\nconst INLINE_GRAPH_DATA = {data_json};\n</script>',
        1
    )

with open('static/graph.html', 'w', encoding='utf-8') as f:
    f.write(new_html)

meta = data['metadata']
print(f"Graph data injected: {meta['node_count']} nodes, {meta['edge_count']} edges")
print(f"Output: static/graph.html")
