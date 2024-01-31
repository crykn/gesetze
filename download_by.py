import os
import re
import requests
import xml.etree.ElementTree as ET
import zipfile

acts = ["BayPAG"]


def to_html_text(element):
    ret = ET.tostring(element, encoding='utf-8').decode("utf-8").replace("satz.nr", "sup").replace("<br />", "") \
        .replace("<absatz.text>", "").replace("</absatz.text>", "").replace("<para.titel>", " ").replace("</para.titel>", "")\
        .replace(' id="xx"', "").replace("<verweis.norm>", "").replace("</verweis.norm>", "").replace("</v.norm>", "") \
        .replace("</v.abk>", "").replace('<symbol id="x">', "").replace('</symbol>', " ").replace("  ", "").replace("\n", "")\
        .replace("<ul>", '<ul style="list-style-type: none;"')
    ret = re.sub(r"<v.norm .*?>", r"", ret)
    ret = re.sub(r"<v.abk .*?>", r"", ret)
    return ret


for act in acts:
    # Download the law as zip file
    response = requests.get("https://www.gesetze-bayern.de/Content/Zip/" + act, stream=True, timeout=60)
    path = os.path.join('tmp/', act + '.zip')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=128):
            file.write(chunk)

    # Work within the zip file
    with zipfile.ZipFile(path, 'r') as zip_file:
        for file_name in zip_file.namelist():
            if file_name.endswith('.xml') and not file_name.endswith('manifest.xml'):
                # zip_file.extract(file_name, 'tmp/')

                # Parse XML file
                tree = ET.parse(zip_file.open(file_name))
                root = tree.getroot()

                statute_abbreviation = root.find("kopf").find("angaben.versabh").find("amtlicheAbk").text # BayPAG

                for child in root.find("rumpf").iter('einzelnorm'):
                    provision_number = child.find('para.nr').text

                    if provision_number is None: # Schlussformel
                        continue

                    provision_name = provision_number + to_html_text(child.find('para.titel'))
                    provision_text = ""
                    no_longer_in_force = False

                    for absatz_element in child.findall('jurAbsatz'):
                        if 'id' in absatz_element.attrib and absatz_element.attrib['id'] == "xxx": # provision is no longer in force
                            no_longer_in_force = True
                            break

                        provision_text += "<p>";

                        absatz_nr_element = absatz_element.find('absatz.nr')
                        if absatz_nr_element is not None:
                            provision_text += absatz_nr_element.text + " "
                        provision_text += to_html_text(absatz_element.find('absatz.text')).replace("<p>", "", 1)

                    if no_longer_in_force:
                        continue

                    # Open file
                    new_path = os.path.join('dist/by/' + act.lower() + '/', provision_number.replace("§ ", "").replace("Art. ", "") + '.html')
                    os.makedirs(os.path.dirname(new_path), exist_ok=True)
                    f = open(new_path, "w", encoding="utf-8")

                    # Write to file
                    f.write("<div class='provision_title'>" + provision_name + "</div>\n<div class='provision_text'>" + provision_text + "</div>")

                    # Close file
                    f.close()

    # Remove the zip file
    os.remove(path)
