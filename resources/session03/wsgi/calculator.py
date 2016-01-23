

def num(s):
    # return some sort of number from a string
    try:
        return int(s)
    except ValueError:
        return float(s)

def multiply(arg1, arg2):
    return("{} * {} = {}".format(arg1, arg2, arg1*arg2))


def add(arg1, arg2):
    return("{} + {} = {}".format(arg1, arg2, arg1+arg2))


def subtract(arg1, arg2):
    return("{} - {} = {}".format(arg1, arg2, arg1-arg2))


def divide(arg1, arg2):
    try:
        return("{} / {} = {}".format(arg1, arg2, arg1/arg2))
    except ZeroDivisionError:
        return("Divide by zero error")



operator = {"add": add, "subtract": subtract, "multiply": multiply,
        "divide": divide}


def resolve_path(path):
    '''
    Try to find one of the operators in the path, then extract the
    arguments from the path

    Check for valid operators and operands

    Return function based on the operator and return operands in a list
    '''
    matchpath = path.lstrip('/')
    parts = matchpath.split('/')
    try:
        func = operator[parts[0]]
    except KeyError:
        raise NameError
    arg1 = num(parts[1])
    arg2 = num(parts[2])
    return(func, arg1, arg2)



def application(environ, start_response):
    headers = [("Content-type", "text/html")]
    try:
        path = environ.get('PATH_INFO', None)
        if path is None:
            raise NameError
        func, arg1, arg2 = resolve_path(path)
        status = "200 OK"
        body = func(arg1, arg2)
    except ValueError:
        status = "200 OK"
        body = "{} contains invalid arguments".format(path)
    except NameError:
        status = "404 Not Found"
        body = "<h1>Not Found</h1>"
    except Exception:
        status = "500 Internal Server Error"
        body = "<h1>Internal Server Error</h1>"
    finally:
        headers.append(('Content-length', str(len(body))))
        start_response(status, headers)
        return [body.encode('utf8')]


if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    srv = make_server('localhost', 8080, application)
    srv.serve_forever()
