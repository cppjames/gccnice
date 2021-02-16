import os
import shutil
import fileinput
import json
import textwrap
import re

color_normal = '\033[0m'
color_gray = '\033[37m'
color_darkgray = '\033[90m'
color_red = '\033[91m'
color_yellow = '\033[93m'
color_cyan = '\033[96m'

def getTerminalWidth():
    return shutil.get_terminal_size((80, 24)).columns

def readMessageJson(): 
    gcc_output = "";
    for line in fileinput.input():
        gcc_output += line

    return json.loads(gcc_output)

def wrap(text, text_width, horizontal = ' ', vertical = ' ',
         top_left = ' ', top_right = ' ', bottom_left = ' ', bottom_right = ' ',
         wrap_horizontal = True, wrap_vertical = True):
   
    final = ''

    if (wrap_vertical): 
        final = (top_left
                + horizontal * text_width
                + top_right
                + '\n')

    final += '\n'.join((vertical if wrap_horizontal else '')
                       + line
                       + ' ' * (text_width - len(removeColorSequences(line)))
                       + (vertical if wrap_horizontal else '')
                       for line in text.split('\n'))

    if (wrap_vertical):
        final += ('\n'
                 + bottom_left
                 + horizontal * text_width
                 + bottom_right)

    return final
    
def removeColorSequences(text):
    return re.sub(r'\x1B\[[\d;]*m', '', text)

def colorText(text, color):
    return color_normal + color + text + color_normal

def underline(color):
    return '\033[4;' + color[2:]

def bold(color):
    return '\033[1;' + color[2:]

def wrapInOutline(text, text_width, label = None, color = color_normal,
                  label_left = True, label_color = None):

    text = wrap(text, text_width,
                horizontal = '\u2500',
                vertical = color + '\u2502' + color_normal,
                top_left = color + '\u256D',
                top_right = '\u256E' + color_normal,
                bottom_left = color + '\u2570',
                bottom_right = '\u256F' + color_normal)

    final_label = label
    if label_color:
        final_label = label_color + label + color;

    label_start = len(color) + (2 if label_left else (text_width - len(label) - 2))
    text = (text[:label_start]
           + ' '
           + final_label
           + ' '
           + text[label_start + len(label) + 2 :])

    return text

def getLocationFile(location):
    return location['caret']['file']

def getLocationLine(location):
    return location['caret']['line']

def getCodeLines(filename, line_min, line_max):
    line_min -= 1
    line_max -= 1
    source_lines = [None for _ in range(line_min, line_max + 1)]
    with open(filename) as source_file:
        for i, line in enumerate(source_file):
            if i >= line_min and i <= line_max:
                source_lines[i - line_min] = line.expandtabs(4)
            elif i > line_max:
                break
    return source_lines

def lineNumberMaxWidth(line):
    # We show 3 lines (line - 1, line, line + 1). The maximum number
    # of digits is the number of digits of the largest line number,
    # which is line + 1.

    # FIXME - This will be too large if the line is the last in the
    # file, and it also happens to be of form 10^n - 1 (at least 999) 
    return max(len(str(line + 1)), 3)

def getLinePrefix(width, number = ' ', color = color_gray):
    spaces = width - len(str(number)) + 1
    padding = '{s:{w}}'.format(w = spaces, s = '')
    line_number = colorText(str(number), color)
    bar = colorText(' \u2502', color_darkgray)
    return padding + line_number + bar

def getCodeBox(location, width, color):
    code_width = width - 2

    location_file = getLocationFile(location)
    location_line = getLocationLine(location)
    code_lines = getCodeLines(location_file, location_line - 1, location_line + 1)
    num_width = lineNumberMaxWidth(location_line)

    code_lines_final = []
    for i, line in enumerate(code_lines):
        if (line == None):
            continue

        wrapped_line = textwrap.fill(line, code_width - 1 - (num_width + 3))
        
        num_color = (bold(color)) if i == 1 else color_gray
        line_prefix = getLinePrefix(num_width, location_line - 1 + i, num_color)

        code_lines_final.append(line_prefix + wrapped_line.split('\n')[0] + '\n')
        for sub_line in wrapped_line.split('\n')[1:]:
            code_lines_final.append(getLinePrefix(num_width) + sub_line + '\n')

    code = ''.join(code_lines_final)[:-1]
    box = wrapInOutline(code, code_width,
                        label = location['caret']['file'],
                        color = color_darkgray, label_color = color_gray,
                        label_left = False)
    return box

def getMessageBox(message, width):
    box_padding = 2
    content_width = width - 2 * box_padding

    content = textwrap.fill(message['message'][0].upper()
                            + message['message'][1:] + ':', content_width)

    label, color = {'w': ('WARNING', color_yellow),
                    'e': ('ERROR', color_red),
                    'n': ('NOTE', color_cyan)}.get(message['kind'][0], (None, color_normal))

    for location in message['locations']:
        content += '\n' + getCodeBox(location, content_width, color)

    if ('children' in message):
        for child in message['children']:
            content += '\n' + getMessageBox(child, content_width)

    box = wrap(content, content_width, wrap_vertical = False)
    box = wrapInOutline(box, content_width + 2, label, color)
    return box

def printMessage(message, width):
    message_box = getMessageBox(message, width - 2)
    for line in message_box.split('\n'):
        print(' ' + line)

if __name__ == '__main__':
    term_width = min(getTerminalWidth(), 60)
    gcc_json = readMessageJson()

    print("")
    for message in gcc_json:
        printMessage(message, term_width)
