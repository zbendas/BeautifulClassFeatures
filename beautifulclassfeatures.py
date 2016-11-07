from bs4 import BeautifulSoup
import re
import argparse

href_stripper = re.compile(r"(<a.*?>)|(</a>)")  # formerly "<a\s+\S+\">|</a>"

strength = re.compile(r" strength | str ", re.IGNORECASE)
dexterity = re.compile(r" dexterity | dex ", re.IGNORECASE)
constitution = re.compile(r" constitution | con ", re.IGNORECASE)
intelligence = re.compile(r" intelligence | int ", re.IGNORECASE)
wisdom = re.compile(r" wisdom | wis ", re.IGNORECASE)
charisma = re.compile(r" charisma | cha ", re.IGNORECASE)

fortitude = re.compile(r" fortitude ", re.IGNORECASE)
reflex = re.compile(r" reflex ", re.IGNORECASE)
will = re.compile(r" will ", re.IGNORECASE)

abilities = [["Strength", strength], ["Dexterity", dexterity], ["Constitution", constitution],
             ["Intelligence", intelligence], ["Wisdom", wisdom], ["Charisma", charisma]]

saves = [["Constitution", fortitude, "Fortitude"], ["Dexterity", reflex, "Reflex"], ["Wisdom", will, "Will"]]


def pre_process(html):
    lead_trail_whitespace = re.compile(r"(^[\s]+)|([\s]+$)", re.MULTILINE)
    html = re.sub(lead_trail_whitespace, '', html)
    html = re.sub('\n', ' ', html)
    html = re.sub('[\s]+<', '<', html)
    html = re.sub('>[\s]+([^\S]|$)', '>', html)
    return html


def mark_abilities(string):
    for ability in abilities:
        string = re.sub(ability[1], ' <mark class="' + ability[0].lower() + '">' + ability[0] + '</mark> ', string)
    return string


def mark_saves(string):
    for save in saves:
        string = re.sub(save[1], ' <mark class="' + save[0].lower() + '">' + save[2] + '</mark> ', string)
    return string


def feature_heads(tag):
    return (not tag.has_attr("class")) and (tag.name == "h4")


def get_feature_names(soup):
    feature_names = []
    for tag in soup.find_all(feature_heads):
        feature_names.append(re.sub(r" *?(\()((Ex)|(Sp)|(Su))[^A-Za-z] *(\)?) *", '', tag.contents[1].string))
    return feature_names


def good_div(tag):
    if tag.has_attr("class"):
        return False
    elif not tag.has_attr("class"):
        return True
    else:
        return False


def flush_to_array(full_text, array):
    # Apply ability score stylization
    full_text = mark_abilities(full_text)
    # Apply saving throw stylization
    full_text = mark_saves(full_text)
    # Replace %mdash; with a regular minus
    full_text = re.sub(r"–", '-', full_text)
    # Fix and escape quotes
    full_text = full_text.replace("’", "'").replace("”", '"').replace('“', '"').replace("'", r"\'").replace('"', r'\"')
    if array.append(full_text):
        return True
    else:
        return False


def recur_for_p(tag, array, full_text=""):
    next_tag = ""
    for sibling in tag.next_siblings:
        if sibling.name == "p" or sibling.name == "ul" or sibling.name == "li" or sibling.name == "a":
            full_text += re.sub(href_stripper, ' ', re.sub('(?<!/)(?<=\")>', '> ', str(sibling)))
        if sibling.name == "div" and good_div(tag):
                full_text += re.sub(href_stripper, ' ', str(sibling))
        if sibling.name == "table":
            # This may help counteract the problems that embedded tables seem to cause
                full_text += ''
        if (sibling.name != "p" and sibling.name != "ul" and sibling.name != "li" and sibling.name != "a"
                and sibling.name != "div" and sibling.name != "table" and sibling.name != "None")\
                or (sibling.name == "div" and not good_div(tag)):
            full_text = re.sub(r'<div class=.*?>.*</div>', '', full_text)
            full_text = re.sub(r' {2,}', ' ', full_text)
            full_text = re.sub(r' \.', '.', full_text)
            full_text = re.sub(r' ,', ',', full_text)
            full_text = re.sub(r'×', 'x', full_text)
            flush_to_array(full_text, array)
            next_tag = sibling
            full_text = ""
            break
    if next_tag.name != "h2":
        recur_for_p(next_tag, array, full_text)
    else:
        return


def get_feature_texts(soup):
    feature_texts = []
    tag = soup.find_all(feature_heads)[0]
    recur_for_p(tag, feature_texts)
    return feature_texts


def main():
    # Set up the command line arguments
    parser = argparse.ArgumentParser(description="From HTML, generate MySQL queries to create Class Features")
    parser.add_argument("-i", "--input", dest="input_file", help="Input file")
    parser.add_argument("-o", "--output", dest="output_file", help="Output file")
    parser.add_argument("-n", "--dry", action="store_const", const=True, dest="dry_run",
                        help="Use this option to do a dry run. No changes will be made.")
    parser.add_argument("-c", "--class", dest="class_id", help="ID of class to add feature to")
    args = parser.parse_args()

    # Main execution code
    with open(args.input_file, 'r') as infile:
        input_html = ""
        for row in infile:
            input_html += row
        processed_in = pre_process(input_html)
        soup = BeautifulSoup(pre_process(processed_in), "lxml")
        names = get_feature_names(soup)
        # print("Feature names: " + str(names))
        texts = get_feature_texts(soup)
        # print("Feature texts: " + str(texts))
        features = list(zip(names, texts))
        if not args.dry_run:
            with open(args.output_file, 'w') as outfile:
                outfile.write('USE pathfinder;\n')
                for name, text in features:
                    outfile.write('INSERT INTO class_features VALUES ('
                                  + args.class_id + ','
                                  + 'NULL,'
                                  + 'NULL,'
                                  + 'NULL,'
                                  + '\"' + str(name) + '\",'
                                  + '\"' + str(text) + '\"'
                                  + ');\n')
        if args.dry_run:
            for name, text in features:
                print('INSERT INTO class_features VALUES ('
                      + args.class_id + ','
                      + 'NULL,'
                      + 'NULL,'
                      + 'NULL,'
                      + '\"' + str(name) + '\",'
                      + '\"' + str(text) + '\"'
                      + ');\n')


if __name__ == "__main__":
    main()
