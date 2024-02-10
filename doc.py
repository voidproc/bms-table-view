import version
import string

def generate_doc(template_file, out_file, mapping):
    with open(template_file, 'rt') as ft:
        template_str = ft.read()
    
    t = string.Template(template_str)
    replaced = t.safe_substitute(mapping)
    
    with open(out_file, 'wt') as fo:
        fo.write(replaced)


mapping = { 'version': version.VERSION }

generate_doc('template/README.template.md', 'README.md', mapping)
generate_doc('template/README.template.txt', 'README.txt', mapping)
generate_doc('template/build.template.bat', 'build.bat', mapping)
