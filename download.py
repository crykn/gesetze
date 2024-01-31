import os
import re
import requests
import xml.etree.ElementTree as ET
import zipfile

acts = ["gg"]


def to_html_text(element):
    # TODO: parse tables: (table, tgroup, colspec, tbody, row, entry)
    ret = ET.tostring(element, encoding='utf-8').decode("utf-8").replace("<Content>", "").replace("</Content>", "")\
        .replace("<SP>", "<P>").replace("</SP>", "</P>").replace("<noindex>", "").replace("</noindex>", "").replace("</LA>", "")
    return re.sub(r"<LA.*?>", r"", ret)


for act in acts:
    # Download the law as zip file
    response = requests.get("https://www.gesetze-im-internet.de/" + act + "/xml.zip", stream=True, timeout=60)
    path = os.path.join('tmp/', act + '.zip')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=128):
            file.write(chunk)

    # Work within the zip file
    with zipfile.ZipFile(path, 'r') as zip_file:
        for file_name in zip_file.namelist():
            if file_name.endswith('.xml'):
                # zip_file.extract(file_name, 'tmp/')

                # Parse XML file
                tree = ET.parse(zip_file.open(file_name))
                root = tree.getroot()

                for child in root.findall('norm'):
                    metadata_element = child.find('metadaten')
                    textdata_element = child.find('textdaten')
                    provision_name_element = metadata_element.find('enbez')

                    statute_abbreviation = metadata_element.find('jurabk').text # GG

                    if provision_name_element is not None: # Each provision, including the Eingangsformel, the Präambel, the Inhaltsübersicht and the Anhang EV
                        provision_number = provision_name_element.text.replace("Art ", "Art. ")  # Art. 1
                        provision_name = provision_number 

                        title_element = metadata_element.find('titel')
                        if  title_element is not None:
                            provision_name += " " + title_element.text

                        if provision_number == "Eingangsformel" or provision_number == "Präambel" or provision_number == "Anhang EV" or provision_number == "Inhaltsübersicht":
                            continue

                        if "(XXXX)" in provision_number: # provision is no longer in force
                            continue

                        # Open file
                        new_path = os.path.join('dist/' + act + '/', provision_number.replace("§ ", "").replace("Art. ", "") + '.html')
                        os.makedirs(os.path.dirname(new_path), exist_ok=True)
                        f = open(new_path, "w", encoding="utf-8")

                        # Write to file
                        provision_text = to_html_text(textdata_element.find('text').find('Content')) # <P>(1) Die Würde...</P><P>(2) Das Deutsche Volk...</P><P>(3) Die nachfolgenden...</P>
                        f.write("<div class='provision_title'>" + provision_name + "</div>\n<div class='provision_text'>" + provision_text + "</div>")

                        footnote_element = textdata_element.find('fussnoten')
                        if footnote_element is not None:
                            footnote_content_element = footnote_element.find('Content')
                            if footnote_content_element is not None:
                                f.write("\n<div class='provision_footnote'>" + to_html_text(footnote_content_element) + "</div>") # Fußnote in <P>-Element

                        # Close file
                        f.close()
    # Remove the zip file
    os.remove(path)
