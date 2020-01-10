from flask import Flask, request, render_template, Response
import os, subprocess, mimetypes
from io import StringIO
from datetime import datetime

app = Flask(__name__, template_folder="")

class CompileError(Exception):
    pass

class Language(object):

    def __init__(self, id, name, selected):
        self.id = id
        self.name = name
        self.selected = selected
        self.last_exec_time = None
        self.last_exec_stdout = None

    def __str__(self):
        return self.name

    def clone(self):
        return Language(self.id, self.name, self.selected)

    def pre_compile(self):
        pass

    def compile(self, code):
        return False

    def post_compile(self):
        pass

    def execute(self, stdin_fp):
        pass

    def post_execute(self):
        pass

    def judge(self, code, stdin_fp):
        self.last_exec_time = None
        self.pre_compile()
        compile_ok = self.compile(code)
        self.post_compile()
        if not compile_ok:
            raise CompileError()
        
        error = None
        try:
            self.execute(stdin_fp)
        except Exception as e:
            error = e
        self.post_execute()

class Java(Language):

    def __init__(self):
        super(Java, self).__init__('java', 'Java', False)
        self.source_file = 'Main.java'
        self.class_file = 'Main.class'
        
    def compile(self, code):
        write_string_to_file(code, self.source_file)
        ret_code, stdout, stderr, exec_time = invoke_command(['javac', self.source_file], None, 10.0)
        self.stdin_fp = self.class_file
        return ret_code == 0

    def execute(self, stdin_fp):
        ret_code, stdout, stderr, exec_time = invoke_command(['java', self.class_file], stdin_fp, 4.0)
        if ret_code == 0:
            self.last_exec_time = exec_time
            self.last_exec_stdout = stdout
        else:
            raise RuntimeError()

    def post_execute(self):
        os.remove(self.source_file)
        os.remove(self.class_file)

class Python(Language):

    def __init__(self):
        super(Python,self).__init__('py', 'Python', False)
        self.source_file = 'source.py'

    def compile(self, code):
        write_string_to_file(code, self.source_file)
        return True

    def execute(self, stdin_fp):
        ret_code, stdout, stderr, exec_time = invoke_command(['python', self.source_file], stdin_fp, 4.0)
        if ret_code == 0:
            self.last_exec_time = exec_time
            self.last_exec_stdout = stdout
        else:
            raise RuntimeError()

    def post_execute(self):
        os.remove(self.source_file)

class C(Language):

    def __init__(self):
        super(C, self).__init__('c', 'C', False)
        self.source_file = 'source.c'
        self.executable_file = 'source'
        
    def compile(self, code):
        write_string_to_file(code, self.source_file)
        ret_code, stdout, stderr, exec_time = invoke_command(['gcc', self.source_file], None, 10.0)
        self.stdin_fp = self.executable_file
        return ret_code == 0

    def execute(self, stdin_fp):
        ret_code, stdout, stderr, exec_time = invoke_command([self.executable_file], stdin_fp, 4.0)
        if ret_code == 0:
            self.last_exec_time = exec_time
            self.last_exec_stdout = stdout
        else:
            raise RuntimeError()

    def post_execute(self):
        os.remove(self.source_file)
        os.remove(self.executable_file)


class CPP(Language):

    def __init__(self):
        super(CPP, self).__init__('cpp', 'C++', False)
        self.source_file = 'source.cpp'
        self.executable_file = 'source'
        
    def compile(self, code):
        write_string_to_file(code, self.source_file)
        ret_code, stdout, stderr, exec_time = invoke_command(['g++', self.source_file], None, 10.0)
        self.stdin_fp = self.executable_file
        return ret_code == 0

    def execute(self, stdin_fp):
        ret_code, stdout, stderr, exec_time = invoke_command([self.executable_file], stdin_fp, 4.0)
        if ret_code == 0:
            self.last_exec_time = exec_time
            self.last_exec_stdout = stdout
        else:
            raise RuntimeError()

    def post_execute(self):
        os.remove(self.source_file)
        os.remove(self.executable_file)


languages = [Java(), Python(), C(), CPP()]

@app.route('/', methods=['POST', 'GET'])
def mainnn():
    title = "CP Checker"
    if request.method == 'GET':
        return render_template('/ui.html', title=title, languages=languages)
    else:
        #{'lang': 'py', 'code': '', 'input-data': '', 'expected-output': '', 'actual-output': ''}
        data = request.form.to_dict()
        write_string_to_file(data['input-data'], 'std.in')

        stdout = exec_time = runtime_error = compile_error = timeout_error = None
        for lang in languages:
            if data['lang'] == lang.id:
                try:
                    lang.judge(data['code'], 'std.in')
                    stdout = lang.last_exec_stdout
                    exec_time = lang.last_exec_time
                except CompileError:
                    compile_error = True
                except TimeoutError:
                    timeout_error = True
                except RuntimeError:
                    runtime_error = True
                break

        os.remove('std.in')

        temp_lang = [x.clone() for x in languages]
        for lang in temp_lang:
            if lang.id == data['lang']:
                lang.selected = True
        return render_template('/ui.html', 
                                title=title,
                                languages=temp_lang, 
                                code=data['code'],
                                input_data=data['input-data'],
                                expected_output=data['expected-output'],
                                actual_output=stdout, 
                                exec_time=exec_time,
                                runtime_error=runtime_error,
                                compile_error=compile_error,
                                timeout_error=timeout_error)

@app.route('/static/<fp>')
def static_file(fp):
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static',fp)
    with open(fp, 'r') as f:
        s = f.read()
    mt = 'application/octet-stream'
    if fp.endswith('css'):
        mt = 'text/css'
    elif fp.endswith('js'):
        mt = 'application/javascript'
    return Response(s, mimetype=mt)


def write_string_to_file(s, fp):
    with open(fp, 'wt', newline='') as f:
        f.write(s.strip())

def invoke_command(command, stdin, timeout):
    start = datetime.now()
    if stdin:
        stdin = open(stdin)
    proc = subprocess.Popen(command, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    ret_code = proc.wait(timeout)
    end = datetime.now()
    return ret_code, out.decode('utf-8'), err.decode('utf-8'), ((end-start).microseconds / 1e6)

if __name__ == "__main__":
    app.run(debug=True)