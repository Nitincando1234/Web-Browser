import socket
import ssl
import tkinter
import tkinter.font
WIDTH,HEIGHT=800,600
SCROLL_STEP=100
HSTEP,VSTEP=13,18
FONTS={}                                    #global fonts directory used for caching

class URL:
    def __init__(self,url):
        self.scheme,url=url.split("://",1)
        assert self.scheme in ['http','https']
        if '/' not in url:
            url=url+'/'
        self.host,url=url.split('/',1)
        self.path='/'+url

        if self.scheme=='http': self.port=80
        elif self.scheme=='https': self.port=443
        if ":" in self.host:
            self.host,self.port=self.host.split(":",1)
    def resolve(self,url):
        if '://' in url: return URL(url)
        if not url.startswith('/'):
            dir,_=self.path.rsplit('/',1)
            while url.startswith('../'):
               _, url=url.split('/',1)
               if '/' in dir:
                   dir,_=dir.rsplit('/',1)
            url=dir+"/"+url
        if url.startswith('//'):
            return URL(self.scheme+":"+url)
        else:
            return URL(self.scheme+"://"+self.host+":"+str(self.port)+url)
    def request(self):
        s=socket.socket(
            family=socket.AF_INET ,      #to create ipv4 connection
            type=socket.SOCK_STREAM,     #for tcp connection type
            proto=socket.IPPROTO_TCP    # for tcp protocole (optional)
        )
        s.connect((self.host,self.port))
        if self.scheme=='https':
            ctx=ssl.create_default_context()
            s=ctx.wrap_socket(s,server_hostname=self.host)
        request="GET {} HTTP/1.0\r\n".format(self.path)
        request+="HOST: {}\r\n".format(self.host)
        request+="\r\n"                 #for the remote server to understand that no new input is sent by us
        s.send(request.encode("utf8"))  #to encode into utf8 binaries
        response=s.makefile("r",encoding='utf8',newline='\r\n')
        statusline=response.readline()
        version,status, explanation=statusline.split(" ",2)
        '''
        headers example:
        HTTP/1.1 200 OK
        Date: Tue, 23 Jun 2024 12:34:56 GMT
        Content-Type: text/html; charset=UTF-8
        Content-Length: 348
        Connection: keep-alive
        Server: Apache/2.4.1 (Unix)
        Cache-Control: no-cache, no-store, must-revalidate
        ETag: "686897696a7c876b7e"
        Set-Cookie: sessionId=abc123; Path=/; HttpOnl'''
        #read headers
        response_headers={}
        while True:
            header_line=response.readline()
            if header_line=='\r\n': break
            header,value=header_line.split(":",1)
            response_headers[header.casefold()]=value.strip()        #casefold to convert headers to lower case
        assert 'transfer-encoding' not in response_headers
        assert 'content-encoding' not in response_headers
        #body of the html
        body=response.read()
        s.close()
        return body
class Text:
    def __init__(self,text,parent):
        self.text=text
        self.parent=parent
        self.children=[]
        self.style={}
    def __repr__(self):
        return repr(self.text)
class element:
    def __init__(self,tag,attributes,parent):
        self.tag=tag
        self.attributes=attributes
        self.parent=parent
        self.children=[]
        self.style={}
    def __repr__(self):
        attrs=[" "+k+"=\""+v+"\""for k, v in self.attributes.items()]
        attr_str=""
        for attr in attrs:
            attr_str+=attr
        return "<"+self.tag+attr_str+">"

def get_font(size,weight,style):
    key=(size,weight,style)
    if key not in FONTS:
        font=tkinter.font.Font(size=size,weight=weight,slant=style)
        label=tkinter.Label(font=font)
        FONTS[key]=(font,label)
    return FONTS[key][0]
def printTree(node,indent=0):
    print(" "*indent,node)
    for child in node.children:
        printTree(child,indent+2)
SELF_CLOSING_TAGS=[
    'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'
]                                  
HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript","link", "meta", "title", "style", "script"
]
INHERITED_PROPERTIES={                              #for fonts
    "font-size":"16px",
    "font-style":"normal",
    "font-weight":"normal",
    "color":"black"
}
class HtmlParser:                                  #converts the HTML document to the tree
    SELF_CLOSING_TAGS=[
    'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'
]   
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript","link", "meta", "title", "style", "script"
]
    def __init__(self,body):
        self.body=body
        self.unfinished=[]
    def implicit_tags(self,tag):
        while True:
            open_tags=[node.tag for node in self.unfinished]
            if open_tags==[] and tag!='html':   
                self.add_tag('html')
            elif open_tags==['html'] and tag not in ['head','body','/html']:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags==['html','head'] and tag not in ['/head']+self.HEAD_TAGS:
                self.add_tag('/head')
            else:
                break
    def add_text(self,text):
        if text.isspace(): return
        self.implicit_tags(None)
        parent=self.unfinished[-1]
        node=Text(text,parent)
        parent.children.append(node)
    def add_tag(self, tag):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"): return
        self.implicit_tags(tag)

        if tag.startswith("/"):
            if len(self.unfinished) == 1: return
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = element(tag, attributes, parent)
            self.unfinished.append(node)
    def get_attributes(self,text):
        attributes={}
        parts=text.split()
        tag=parts[0].casefold()
        for attrpair in parts[1:]:
            if '=' in attrpair:
                key,value=attrpair.split("=",1)
                if len(value)>2 and value[0] in ["'","\""]:
                    value=value[1:-1]
                attributes[key.casefold()]=value
            else:
                attributes[attrpair.casefold()]=''
        return tag,attributes
    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished)>1:
            node =self.unfinished.pop()
            parent=self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()
    def parse(self):
        buffer = ""
        in_tag = False
        for c in self.body:
            if c == "<":
                in_tag = True
                if buffer: self.add_text(buffer)
                buffer = ""
            elif c == ">":
                in_tag = False
                self.add_tag(buffer)
                buffer = ""
            else:
                buffer += c
        if not in_tag and buffer:
            self.add_text(buffer)
        return self.finish()
def paintTree(layout_object,display_list):
    display_list.extend(layout_object.paint())
    for child in layout_object.children:
        paintTree(child,display_list)
class DocumentLayout:
    def __init__(self,node):
        self.node=node
        self.parent=None
        self.children=[]
        self.previous=None
        #self.x,self.y,self.width,self.height=None,None,None,None
    def paint(self):
        return []
    def layout(self):
        child=BlockLayout(self.node,self,None)
        self.children.append(child)
        self.width=WIDTH-2*HSTEP
        self.x=HSTEP
        self.y=VSTEP
        child.layout()
        self.height=child.height
BLOCK_ELEMENTS=["html", "body", "article", "section", "nav", 
    "aside","h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote","ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset","legend", "details", "summary"
]
class BlockLayout:

    def __init__(self,node,parent,previous):
        self.node=node
        self.parent=parent
        self.previous= previous
        self.children=[]
        self.display_list=[]
        self.x=None
        self.y=None
        self.height=None
        self.width=None
    def recurse(self,node):
        if isinstance(node,Text):
            for word in node.text.split():
                self.word(node,word)
        else:
            if node.tag=='br':
                self.flush()
            for child in node.children:
                self.recurse(child)

    def flush(self):
        if not self.line: return
        metrics=[font.metrics() for x,word,font,color in self.line]
        max_ascent=max([metric['ascent'] for metric in metrics])
        baseline=self.cursor_y+1.25*max_ascent
        for rel_x, word,font,color in self.line:
            x=rel_x+self.x
            y=self.y+baseline-font.metrics('ascent')
            self.display_list.append((x,y,word,font,color))
        self.cursor_x=self.x
        max_descent=max([metric['descent'] for metric in metrics])
        self.cursor_y=baseline+1.25*max_descent
        #self.cursor_x=HSTEP
        self.line=[]
    def word(self,node,word):
        weight=node.style['font-weight']
        style=node.style['font-style']
        if style=='normal': style='roman'
        size=int(float(node.style['font-size'][:-2])*.75)
        font=get_font(size,weight,style)
        w=font.measure(word)
        space_width=font.measure(" ")
        if self.cursor_x+w>=self.width:
            self.flush()
        color=node.style['color']
        self.line.append((self.cursor_x,word,font,color))
        self.cursor_x+=w+space_width
    def paint(self):
        cmds = []
        bgcolor=self.node.style.get("background-color","transparent")

        if bgcolor!='transparent':
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
            cmds.append(rect)

        if self.layout_mode() == "inline":
            for x, y, word, font,color in self.display_list:
                cmds.append(DrawText(x, y, word, font,color))
        return cmds
    def layout(self):
        if self.previous:
            self.y=self.previous.height+self.previous.y
        else:
            self.y=self.parent.y
        self.x=self.parent.x
        self.width=self.parent.width
        mode=self.layout_mode()                         # for getting the mode of layout
        if mode=='block':
            previous=None
            for child in self.node.children:
                next=BlockLayout(child,self, previous)
                self.children.append(next)
                previous=next
        else:
            self.cursor_x=0
            self.cursor_y=0
            self.weight='normal'
            self.style='roman'
            self.size=12
            self.line=[]
            self.recurse(self.node)
            self.flush()
        for child in self.children:
            child.layout()
        if mode=='block':
            self.height=sum([child.height for child in self.children])
        else:
            self.height = self.cursor_y
    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"


class TagSelector:
    def __init__(self,tag):
        self.tag=tag
        self.priority=1
    def matches(self,node):
        return isinstance(node,element) and self.tag==node.tag
class DescendantSelector:
    def __init__(self,anscestor,descendent):
        self.anscestor=anscestor
        self.descendant=descendent
        self.priority=anscestor.priority+descendent.priority
    def matches(self,node):
        if not self.descendant.matches(node): return False
        while node.parent:
            if self.anscestor.mathces(node.parent): return True
            node =node.parent
        return False
class CSSparser:

    def __init__(self,s):
        self.s=s
        self.i=0
    def parse(self):
        rules=[]
        while self.i<len(self.s):
            try:
                self.whitespace()
                selector=self.selector()
                self.literal('{')
                self.whitespace()
                body=self.body()
                self.literal('}')
                rules.append((selector,body))
            except Exception:
                why=self.ignore_until(['}'])
                if why=='}':
                    self.literal('}')
                    self.whitespace()
                else: 
                    break
        return rules
    def selector(self):
        out=TagSelector(self.word().casefold())
        self.whitespace()
        while self.i<len(self.s) and self.s[self.i]!='{':
            tag=self.word()
            descendant=TagSelector(tag.casefold())
            out=DescendantSelector(out,descendant)
            self.whitespace()
        return out

    def whitespace(self):
        while self.i<len(self.s) and self.s[self.i].isspace():
            self.i+=1                                #increments i for every whitespace
    def word(self):
        start=self.i
        while self.i<len(self.s):
            if self.s[self.i].isalnum() or self.s[self.i] in "#-.%":
                self.i+=1
            else:
                break
        if not (self.i>start):
            raise Exception("Parsing Error !")
        return self.s[start: self.i]
    def literal (self,literal):
        if not(self.i< len(self.s) and self.s[self.i] == literal):
            raise Exception("Parsing Error !")
        self.i+=1
    def pair(self):
        property=self.word()
        self.whitespace()
        self.literal(":")
        self.whitespace()
        value=self.word()
        return property.casefold(),value
    def body(self):
        pairs={}
        while self.i<len(self.s) and self.s[self.i] !="}":
            try:
                property,value=self.pair()
                pairs[property.casefold()]=value
                self.whitespace()
                self.literal(';')
                self.whitespace()
            except Exception:
                why=self.ignore_until([';','}'])
                if why==';':
                    self.literal(';')
                    self.whitespace()
                else :
                    break
        return pairs
    def ignore_until(self,chars):
        while self.i<len(self.s):
            if self.s[self.i] in chars:
                return self.s[self.i]
            else:
                self.i+=1
        return None
DEFAULT_STYLE_SHEET=CSSparser(open('browser.css').read()).parse()
class DrawText:
    def __init__(self,x1,y1,text, font,color) :
        self.left=x1
        self.top=y1
        self.text=text
        self.font=font
        self.color=color
        self.bottom=y1+font.metrics('linespace')
    def execute(self,scroll,canvas):
        canvas.create_text(
            self.left,
            self.top-scroll,
            text=self.text,
            font=self.font,
            anchor='nw',
            fill=self.color
        )
class DrawRect:
    def __init__(self,x1,y1,x2,y2,color):
        self.left=x1
        self.right=x2
        self.top=y1
        self.bottom=y2
        self.color=color
    def execute(self,scroll,canvas):
        canvas.create_rectangle(
            self.left,
            self.top-scroll,
            self.right,
            self.bottom-scroll,
            width=0,                            #for background made the width of line border to zero
            fill=self.color
        )
def style(node,rules):
    node.style={}
    for property,default_values in INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property]=node.parent.style[property]
        else:
            node.style[property]=default_values
    # to over ride the inline styles that are particular to an html element only
    for selector,body in rules:
        if not selector.matches(node): continue
        for property ,value in body.items():
            node.style[property]=value
    if isinstance(node,element) and "style" in node.attributes:
        pairs=CSSparser(node.attributes["style"]).body()
        for property,value in pairs.items():
            node.style[property]=value
    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size=node.parent.style["font-size"]
        else:
            parent_font_size=INHERITED_PROPERTIES["font-size"]           #note that this value is in px and if node's parent is existing than it is in %
        node_pct=float(node.style["font-size"][:-1])/100
        parent_px=float(parent_font_size[:-2])
        node.style["font-size"]=str(node_pct*parent_px)+"px"
    for child in node.children:
        style(child,rules)
def tree_to_list(tree, list):
    list.append(tree)
    for child in tree.children:
        tree_to_list(child, list)
    return list
def cascade_priority(rule):
    selector,body=rule
    return selector.priority
class Browser:
    def __init__(self) :
        self.scroll=0
        self.window=tkinter.Tk()                 #creates a widget on screen ---> (window)
        self.canvas=tkinter.Canvas(self.window,width=WIDTH,height=HEIGHT,bg="white")
        self.canvas.pack()
        self.window.bind('<Down>',self.scroller)
        self.text_list=[]
        self.nodes=[]
        #self.font=tkinter.font.Font(
            #family='Times',
            #size=16,
            #weight='bold',
            #lant='italic' 
            
        #)
    def draw(self):
        self.canvas.delete('all')
        for cmd in self.text_list:
            if cmd.top>self.scroll+HEIGHT: continue
            if cmd.bottom<self.scroll: continue
            cmd.execute(self.scroll,self.canvas)
    def scroller(self, e):
        max_y = max(self.document.height + 2*VSTEP - HEIGHT, 0)
        self.scroll = min(self.scroll + SCROLL_STEP, max_y)
        self.draw()
    def load(self,url):
        body=url.request()
        self.nodes=HtmlParser(body).parse()
        rules=DEFAULT_STYLE_SHEET.copy()
        links=[ node.attributes['href']
               for node in tree_to_list(self.nodes,[])
               if isinstance(node,element)
               and node.tag=='link'
               and node.attributes.get('rel')=='stylesheet'
               and 'href' in node.attributes
                ]
        for link in links:
            style_url=url.resolve(link)
            try:
                body=style_url.request()
            except:
                continue
            rules.extend(CSSparser(body).parse())
        style(self.nodes,sorted(rules,key=cascade_priority))
        #printTree(self.nodes)
        self.document=DocumentLayout(self.nodes)
        self.document.layout()
        self.text_list=[]
        paintTree(self.document,self.text_list)
        self.draw()

if __name__=="__main__":        #if .py file run as its own name will be=.that_file. .py if imported than the file_in_which_imported.py act as main function with args
    import sys
    Browser().load(URL(sys.argv[1]))
    tkinter.mainloop()
