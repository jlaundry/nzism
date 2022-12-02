
import argparse
import difflib
import json
import xml.etree.ElementTree as xee

from jinja2 import Environment, FileSystemLoader
jinja2_env = Environment(loader=FileSystemLoader('templates'))

"""
<xml>
	<chapter title="1. About information security">
		<section title="1.1. Understanding and using this Manual">
			<subsection title="Rationale &amp; Controls">
				<block title="1.1.65. Justification for non-compliance">
					<paragraph title="1.1.65.C.01." classifications="All Classifications" compliances="Must" CID="131">
"""

def sortkey(title):
    """Returns a alphabetically-sortable key based on the NZISM title.
    
    Example: sortkey('1.1.65.C.01.') -> '001001065001'"""
    output = ""
    for x in [0,1,2,4]:
        output = "{0}{1:03d}".format(output, int(title.split(".")[x]))
    return output


def diff_text(old_text, new_text):
    """Returns a HTML-formatted string with differences between old and new text."""
    sequence = difflib.SequenceMatcher(None, old_text, new_text)
    output = []
    for opcode, a0, a1, b0, b1 in sequence.get_opcodes():
        if opcode == 'equal':
            output.append(sequence.a[a0:a1])
        elif opcode == 'insert':
            output.append("<span class=\"insert\">{}</span>".format(sequence.b[b0:b1]))
        elif opcode == 'delete':
            output.append("<span class=\"delete\">{}</span>".format(sequence.a[a0:a1]))
        elif opcode == 'replace':
            output.append("<span class=\"delete\">{}</span><span class=\"insert\">{}</span>".format(sequence.a[a0:a1], sequence.b[b0:b1]))
        else:
            raise RuntimeError("unexpected opcode")
    return ''.join(output)


def compare_files(old, new, output_file):
    old_doc = xee.parse(old)
    old_cids = set()
    for el in old_doc.findall('.//paragraph[@CID]'):
        cid = int(el.attrib['CID'])
        old_cids.add(cid)

    new_doc = xee.parse(new)
    new_cids = set()
    for el in new_doc.findall('.//paragraph[@CID]'):
        cid = int(el.attrib['CID'])
        new_cids.add(cid)

    controls_added = []
    controls_removed = []
    controls_changed = []

    # List of controls added
    for cid in list(new_cids - old_cids):
        el = new_doc.find(f".//paragraph[@CID='{cid}']")

        control = {
            "CID": cid,
            "sortkey": sortkey(el.attrib['title']),
            "title": el.attrib['title'],
            "classifications": el.attrib['classifications'],
            "compliances": el.attrib['compliances'],
            "text": el.text,
        }
        controls_added.append(control)

    # List of controls removed
    for cid in list(old_cids - new_cids):
        el = old_doc.find(f".//paragraph[@CID='{cid}']")

        control = {
            "CID": cid,
            "sortkey": sortkey(el.attrib['title']),
            "title": el.attrib['title'],
            "classifications": el.attrib['classifications'],
            "compliances": el.attrib['compliances'],
            "text": el.text,
        }
        controls_removed.append(control)

    # List of controls changed
    for cid in list(old_cids & new_cids):
        old_el = old_doc.find(f".//paragraph[@CID='{cid}']")
        new_el = new_doc.find(f".//paragraph[@CID='{cid}']")

        if old_el.text == new_el.text:
            continue

        control = {
            "CID": cid,
            "sortkey": sortkey(new_el.attrib['title']),
            "title": new_el.attrib['title'],
            "classifications": new_el.attrib['classifications'],
            "compliances": new_el.attrib['compliances'],
            "text": diff_text(old_el.text, new_el.text),
        }
        controls_changed.append(control)

    report_template = jinja2_env.get_template('report.jinja2')
    rendered = report_template.render(
        old = old,
        new = new,
        controls_added = controls_added,
        controls_removed = controls_removed,
        controls_changed = controls_changed,
    )
    output_file.write(rendered)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compare NZISM versioned XML files.')

    with open('config.json', 'r') as of:
        config = json.load(of)

    comparisons = []
    versions = []

    for (i, base) in enumerate(config):
        versions.append(base['version'])
        for j in range(i+1, len(config)):
            new = config[j]
            print(f"Comparing {base['version']} to {new['version']}")
            comparisons.append((base, new,))
            output_filename = f"NZISM-{base['version']}-to-{new['version']}.html"
            with open(output_filename, 'w') as output_file:
                compare_files(base['filename'], new['filename'], output_file)

    matrix = {}
    for i in versions:
        matrix[i] = {}
        for j in versions:
            matrix[i][j] = False

    for (x,y) in comparisons:
        matrix[x['version']][y['version']] = True

    index_template = jinja2_env.get_template('index.jinja2')
    rendered = index_template.render(
        matrix = matrix,
        most_recent = [(x,y) for (x,y) in comparisons if y==base],
        versions = versions,
    )
    with open('index.html', 'w') as output_file:
        output_file.write(rendered)
