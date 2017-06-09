# -*- coding: utf-8 -*-
__author__ = 'sergey.o.a@gmail.com'
from pdfminer.pdfparser import PDFParser, PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator
import re
import pdfminer
import logging


class Document:
    def __init__(self, file):
        self.__file = file
        parser = PDFParser(file)
        doc = PDFDocument()
        parser.set_document(doc)
        doc.set_parser(parser)
        doc.initialize('')
        rsrcmgr = PDFResourceManager()
        laparams = LAParams()
        self.__device = PDFPageAggregator(rsrcmgr, laparams = laparams)
        self.__interpreter = PDFPageInterpreter(rsrcmgr, self.__device)
        self.__pages = doc.get_pages()
        self.metadata = doc.info
        self.raws = []
        self.mini_blocks = []
        self.elements_from_pdf = {}
        self.table_array = []
        self.unsort_elems = []
        self.table_raws = []
        self.merged_unsort_elems = []

    @staticmethod
    def __extract_elements_from_page(list_objects):
        """Private method for parse one page from PDF file
        ""return elements
        """
        result = []
        try:
            for obj in list_objects:
                if isinstance(obj, pdfminer.layout.LTTextBoxHorizontal):
                    if isinstance(obj._objs[0], pdfminer.layout.LTTextLineHorizontal):
                        for i in range(0, len(obj._objs)):
                            result.append({'text': obj._objs[i].get_text().replace('\n', ' '),
                                           'x0': obj._objs[i].x0,
                                           'x1': obj._objs[i].x1,
                                           'y0': obj._objs[i].y0,
                                           'y1': obj._objs[i].y1,
                                           'height': obj._objs[i].height,
                                           'width': obj._objs[i].width
                                           })
                    else:
                        result.append({'text': obj.get_text().replace('\n', ' '),
                                       'x0': obj.x0,
                                       'x1': obj.x1,
                                       'y0': obj.y0,
                                       'y1': obj.y1,
                                       'height': obj.height,
                                       'width': obj.width
                                       })
            return result
        except:
            print('Error of extracting')
            return result

    def get_table_array(self, num_page = 1):
        """Getting table array from table elements from PDF file"""
        logging.info('Getting table from PDF file')
        border = []
        self.sort_elements(num_page = num_page)
        t_raws = list(self.table_raws)
        # if len(self.table_raws) == 0:
        #     self.sort_elements(num_page = num_page)
        #     t_raws = list(self.table_raws)
        # else:
        #     t_raws = list(self.table_raws)
        flag = False
        for i in range(0, len(t_raws)):
            if (len(t_raws[i]) == self.max_count_elements) and not flag:
                flag = True
                for j in range(0, self.max_count_elements):
                    if (j != self.max_count_elements - 1) and (j != 0):
                        border.append((((t_raws[i][j-1]['x1'] + t_raws[i][j]['x0']) / 2), ((t_raws[i][j]['x1'] + t_raws[i][j+1]['x0']) / 2)))
                    elif j == self.max_count_elements - 1:
                        border.append(((t_raws[i][j-1]['x1'] + t_raws[i][j]['x0']) / 2, t_raws[i][j]['x1']))
                    else:
                        border.append((t_raws[i][j]['x0'], (t_raws[i][j]['x1'] + t_raws[i][j+1]['x0']) / 2))


        n, m = len(t_raws), self.max_count_elements
        table_array = [[0 for i in range(m)] for j in range(n)]

        for i in range(0, len(t_raws)):
            for j in range(0, len((t_raws[i]))):
                for k in range(0, self.max_count_elements):
                    if (t_raws[i][j]['x0']+7 >= border[k][0]) and (t_raws[i][j]['x1']-7 <= border[k][1]):
                        table_array[i][k] = t_raws[i][j]

        self.table_array = table_array
        return table_array

    @staticmethod
    def __check_reg(text, reg_exp):
        """Check regular expression"""
        pre_match = re.search(r""+reg_exp, str(text))
        if pre_match != None:
            match = pre_match.group()
            if str(match) == text.decode('utf-8'):
                return True
            else:
                return False
        else:
            return False

    @staticmethod
    def __get_max_for_block(block, coordinate):
        """Get maximum by coordinate block"""
        maximum = 0
        for elem in block:
            if elem[coordinate] > maximum:
                maximum = elem[coordinate]
        return maximum

    @staticmethod
    def __get_min_for_block(block, coordinate):
        """Get minimum by coordinate block"""
        minimum = block[0][coordinate]
        for elem in block:
            if elem[coordinate] < minimum:
                minimum = elem[coordinate]
        return minimum

    @staticmethod
    def __get_coordinate_block(block):
        """Get all coordinate for block"""
        max_y1 = Document.__get_max_for_block(block, 'y1')
        min_y0 = Document.__get_min_for_block(block, 'y0')
        max_x1 = Document.__get_max_for_block(block, 'x1')
        min_x0 = Document.__get_min_for_block(block, 'x0')
        return max_x1, max_y1, min_y0, min_x0

    @staticmethod
    def __get_text_from_block(block):
        """Get New text for block which contain any elements"""
        text = ''
        for elem in block:
            text = text + ' ' + elem['text']
        return text

    def get_mini_blocks(self, num_page = 1, reg_exp = "[ ]*[0-9]*[ ]*%[ ]*"):
        """Get mini blocks from elements"""
        if len(self.mini_blocks) != 0:
            return self.mini_blocks

        elements = self.elements_from_pdf[num_page]
        mini_blocks = {}
        y = 0
        a = []
        for i in range(0, len(elements)):
            if i not in a:
                mini_blocks.update({y: [elements[i]]})
                for j in range(i + 1, len(elements)):
                    if (abs(elements[i]['y0'] - elements[j]['y1']) <= elements[i]['height']) and \
                            (abs(elements[i]['y0'] - elements[j]['y1']) > 0.5) and \
                            (abs(elements[i]['x0'] - elements[j]['x0']) <= elements[i]['width']) and \
                            (Document.__check_reg(elements[j]['text'].encode('utf-8'), reg_exp)):
                        mini_blocks[y].append(elements[j])
                        a.append(j)
                y += 1
        elements = []
        for mini_block in mini_blocks.values():
            if len(mini_block) == 1:
                elements.append(mini_block[0])
            else:
                x1, y1, y0, x0 = Document.__get_coordinate_block(mini_block)
                text = Document.__get_text_from_block(mini_block)
                width = x1 - x0
                height = y1 - y0
                elements.append({'x0': x0,
                                 'y0': y0,
                                 'x1': x1,
                                 'y1': y1,
                                 'text': text,
                                 'height': height,
                                 'width': width
                                 })
        self.mini_blocks = elements
        return elements

    def merge_unsorted_elements(self):
        u_elements = list(self.unsort_elems)
        mini_blocks = {}
        y = 0
        a = []
        for i in range(0, len(u_elements)):
            if i not in a:
                mini_blocks.update({y: [u_elements[i]]})
                for j in range(i + 1, len(u_elements)):
                    if (abs(u_elements[i]['y0'] - u_elements[j]['y1']) <= u_elements[i]['height'] * 3) and \
                            (abs(u_elements[i]['y0'] - u_elements[j]['y0']) > 0.5) and (abs(u_elements[i]['x0'] - u_elements[j]['x0']) <= 10):
                        mini_blocks[y].append(u_elements[j])
                        a.append(j)
                y += 1
        self.merged_unsort_elems = mini_blocks





    def get_raws(self, num_page = 1):
        """Get raws from elements"""
        elements = self.mini_blocks
        raws = {}
        if len(elements) == 0:
            elements = self.get_mini_blocks(num_page = num_page)
        y = 0
        a = []
        for i in range(0, len(elements)):
            if i not in a:
                raws.update({y: [elements[i]]})
                for j in range(i + 1, len(elements)):
                    if elements[i]['y1'] == elements[j]['y1']:
                        raws[y].append(elements[j])
                        a.append(j)
                y += 1
        self.raws = raws
        return raws

    @staticmethod
    def __max_count_elements_in_raws(raws):
        """Get max count elements in raw"""
        max_count = 0
        for raw in raws.values():
            if len(raw) > max_count:
                max_count = len(raw)
        return max_count

    @staticmethod
    def __sort_raws(raws, max_count):
        """Sort all raws by unsort elements and table elements and table raws"""
        unsorted_elements = []
        table_elements = []
        table_raws = []
        for raw in raws.values():
            if len(raw) >= 0.8 * max_count:
                table_raws.append(raw)
                for table_elem in raw:
                    table_elements.append(table_elem)
            else:
                for u_elem in raw:
                    unsorted_elements.append(u_elem)

        return unsorted_elements, table_elements, table_raws

    @staticmethod
    def __merge_elements(unsort_elems, table_elems, reverse = False):
        """Merge unsort elements with table elements by coordinate
        ""if 'reverse' = 'False': merge by top to down
        ""if 'reverse' = 'True': merge by down to top
        """
        u_elems = list(unsort_elems)
        if not reverse:
            for i in range(0, (len(unsort_elems))):
                for j in range(0, (len(table_elems))):
                    if (abs(unsort_elems[i]['x0'] - table_elems[j]['x0']) <= 5) or\
                            (abs(((unsort_elems[i]['x0'] + unsort_elems[i]['x1']) / 2) - ((table_elems[j]['x0'] + table_elems[j]['x1']) / 2)) <= 10) or \
                            ((unsort_elems[i]['x0'] >= table_elems[j]['x0']) and (unsort_elems[i]['x1'] <= (table_elems[j]['x0'] + table_elems[j]['width']))):
                        if (unsort_elems[i]['y0'] > table_elems[j]['y0']) and\
                                (abs(unsort_elems[i]['y0'] - table_elems[j]['y1']) < 3):
                            block = [unsort_elems[i], table_elems[j]]
                            u_elems[i] = 0
                            x1, y1, y0, x0 = Document.__get_coordinate_block(block)
                            text = Document.__get_text_from_block(block)
                            width = x1 - x0
                            height = y1 - y0
                            table_elems[j].update({'x0': x0,
                                                   'y0': y0,
                                                   'x1': x1,
                                                   'y1': y1,
                                                   'text': text,
                                                   'height': height,
                                                   'width': width
                                                   })
                        if (unsort_elems[i]['y0'] < table_elems[j]['y0']) and\
                                (abs(table_elems[j]['y0'] - unsort_elems[i]['y1']) < 3):
                            block = [table_elems[j], unsort_elems[i]]
                            u_elems[i] = 0
                            x1, y1, y0, x0 = Document.__get_coordinate_block(block)
                            text = Document.__get_text_from_block(block)
                            width = x1 - x0
                            height = y1 - y0
                            table_elems[j].update({'x0': x0,
                                                   'y0': y0,
                                                   'x1': x1,
                                                   'y1': y1,
                                                   'text': text,
                                                   'height': height,
                                                   'width': width,
                                                   })
        else:
            for i in reversed(range(0, (len(unsort_elems)))):
                for j in reversed(range(0, (len(table_elems)))):
                    if (abs(unsort_elems[i]['x0'] - table_elems[j]['x0']) <= 5) or\
                            (abs(((unsort_elems[i]['x0'] + unsort_elems[i]['x1']) / 2) - ((table_elems[j]['x0'] + table_elems[j]['x1']) / 2)) <= 10) or \
                            ((unsort_elems[i]['x0'] >= table_elems[j]['x0']) and (unsort_elems[i]['x1'] <= (table_elems[j]['x0'] + table_elems[j]['width']))):
                        if (unsort_elems[i]['y0'] > table_elems[j]['y0']) and\
                                (abs(unsort_elems[i]['y0'] - table_elems[j]['y1']) < 5):
                            block = [unsort_elems[i], table_elems[j]]
                            u_elems[i] = 0
                            x1, y1, y0, x0 = Document.__get_coordinate_block(block)
                            text = Document.__get_text_from_block(block)
                            width = x1 - x0
                            height = y1 - y0
                            table_elems[j].update({'x0': x0,
                                                   'y0': y0,
                                                   'x1': x1,
                                                   'y1': y1,
                                                   'text': text,
                                                   'height': height,
                                                   'width': width
                                                   })
                        if (unsort_elems[i]['y0'] < table_elems[j]['y0']) and\
                                (abs(table_elems[j]['y0'] - unsort_elems[i]['y1']) < 5):
                            block = [table_elems[j], unsort_elems[i]]
                            u_elems[i] = 0
                            x1, y1, y0, x0 = Document.__get_coordinate_block(block)
                            text = Document.__get_text_from_block(block)
                            width = x1 - x0
                            height = y1 - y0
                            table_elems[j].update({'x0': x0,
                                                   'y0': y0,
                                                   'x1': x1,
                                                   'y1': y1,
                                                   'text': text,
                                                   'height': height,
                                                   'width': width,
                                                   })


        indexes = reversed(range(0, len(u_elems)))
        for index in indexes:
            if u_elems[index] == 0:
                u_elems.pop(index)
        # Change flag to run merge elements by down to top
        if not reverse:
            u_elems, table_elems = Document.__merge_elements(u_elems, table_elems, reverse = True)
            return u_elems, table_elems

        return u_elems, table_elems

    def sort_elements(self, num_page = 1):
        """Sort elements"""
        logging.info('Sorting elements...')
        self.raws = self.get_raws(num_page = num_page)
        # if len(self.raws) == 0:
        #     self.raws = self.get_raws(num_page = num_page)
        max_count_elements = Document.__max_count_elements_in_raws(self.raws)
        self.max_count_elements = max_count_elements
        unsort_elem, table_elems, table_raws = Document.__sort_raws(self.raws, max_count_elements)
        unsort_elements, table_elements = Document.__merge_elements(unsort_elem, table_elems)
        self.table_raws = table_raws
        self.unsort_elems = unsort_elements
        self.table_elems = table_elements

    def get_elements_from_pages(self):
        """Extracting all elements from PDF pages
        "" self.elements_from_pdf
        """
        i = 1
        for page in self.__pages:
            self.__interpreter.process_page(page)
            layout = self.__device.get_result()
            elements_from_pdf = Document.__extract_elements_from_page(layout._objs)
            elements = sorted(elements_from_pdf, key = lambda element: (element['y0'], -element['x0']))
            elements.reverse()
            self.elements_from_pdf.update({i: elements})
            i += 1

def print_mini_blocks(mini_blocks):
    for mini_block in mini_blocks:
        print('-----|-----')
        print(mini_block['text'])

def print_raws(raws):
    for raw in raws.values():
        print('-----|NEW RAW|-----')
        for elem in raw:
            print(elem['text'])

def print_table_elems(table_elems):
    for elem in table_elems:
        print('-----|-----')
        print((elem['text']))

def print_unsort_elements(unsort_elems) :
    for elem in unsort_elems:
        print('-----|-----')
        print((elem['text']))

def print_table(table_array):
    for row in table_array:
        for elem in row:
            try :
                print(elem['text'], end = '|')
            except :
                print(elem, end = '|')
        print()

def get_html_file(table, paragraphs):
    file = open('index.html', 'a')

    message = """<html>
    <head></head>
        <body><p>Data from your PDF file!</p>"""

    msa = "<table border='5px' align-text='left'>"
    for raw in table:
        msa = msa + "<tr>"
        for elem in raw:
            try:
                text = elem['text']
                msa = msa + "<td>" + text + "</td>"
            except:
                msa = msa + "<td>" + str(elem) + "</td>"
        msa = msa + "</tr>"

    table_html = msa + "</table>"
    msa = "<div>"
    for paragraph in paragraphs.values():
        msa = msa + "<hr>" + "<div>"
        for raw in paragraph:
            msa = msa + "<p>" + raw['text'] + "</p>"
        msa = msa + "</div>"
    message = message + msa + "<br></br>" + table_html + "</body></html>"
    file.write(message)

if __name__ == "__main__":
    try:
        logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s',
                            level = logging.DEBUG)
        logging.info('Open PDF file')

        # Open a PDF file.
        print("Please enter [filename].pdf")
        file_name = input()
        pdf_file = open(file_name, 'rb')
        logging.info('PDF file is open')
        # Create Document object
        document = Document(pdf_file)
        document.get_elements_from_pages()
        elements = document.elements_from_pdf
        logging.info('Extract finished')
        print("Enter page number:")
        # num_page = int(input())
        for num_page in range(0, len(document.elements_from_pdf) + 1):
            if num_page > len(document.elements_from_pdf):
                print('end')
            elif num_page != 0:
                #  # Get mini-blocks by rexexp or without regexp
                # document.get_mini_blocks(num_page = num_page, reg_exp = "[ ]*[0-9]*[ ]*%[ ]*")
                # print('-----Mini_blockS----')
                # # print_mini_blocks(document.mini_blocks)
                # document.get_raws(num_page = num_page)
                # print('----RAWS-----')
                # # print_raws(document.raws)
                # document.sort_elements(num_page = num_page)
                # print('--------UNSORTED ELEMENTS-----')
                # # print_unsort_elements(document.unsort_elems)
                # print('--------TABLE ELEMENTS-------')
                # # print_table_elems(document.table_elems)
                document.get_table_array(num_page = num_page)
                print('-----Print table from PDF file-----')
                document.merge_unsorted_elements()
                get_html_file(document.table_array, document.merged_unsort_elems)

                document.raws = []
                document.mini_blocks = []
                document.table_array = []
                document.unsort_elems = []
                # print_table(document.table_array)
                print("---------End PAGE---------")
    except:
        print('File not found!')
