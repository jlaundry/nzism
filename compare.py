
import argparse
import difflib
import xml.etree.ElementTree as xee

from jinja2 import Environment, FileSystemLoader

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Compare NZISM versioned XML files.')

    parser.add_argument(
        '--old',
        type=argparse.FileType('r'),
        default="nzism-data/NZISM-FullDoc-V.3.5-January-2022.xml",
        help='Old (previous) version to compare',
    )

    parser.add_argument(
        '--new',
        type=argparse.FileType('r'),
        default="nzism-data/NZISM-FullDoc-V.3.6-September-2022.xml",
        help='New (next) version to compare',
    )

    parser.add_argument(
        '--output_filename',
        type=argparse.FileType('w'),
        default="comparison.html",
        help='Output HTML filename',
    )

    args = parser.parse_args()

    old_doc = xee.parse(args.old)
    old_cids = set()
    for el in old_doc.findall('.//paragraph[@CID]'):
        cid = int(el.attrib['CID'])
        old_cids.add(cid)

    new_doc = xee.parse(args.new)
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

    jinja2_env = Environment(loader=FileSystemLoader('templates'))
    report_template = jinja2_env.get_template('report.jinja2')

    output = report_template.render(
        args = args,
        controls_added = controls_added,
        controls_removed = controls_removed,
        controls_changed = controls_changed,
    )
    args.output_filename.write(output)
