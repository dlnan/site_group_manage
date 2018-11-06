import datetime
import random
import time
import os
import json

# from celery import Celery
from flask import Flask, render_template, Response, request, redirect, url_for, jsonify
import pymysql.cursors
from jinja2 import Environment, FileSystemLoader
import paramiko

from core.Generator import generator
from flask_celery import make_celery
from service.SiteService import batch_add_site
from utils.regex_utils import re_web_url

app = Flask(__name__)

# celery = Celery('app', broker='redis://localhost:6379/1')
# app.config.update(
#     CELERY_BROKER_URL='redis://localhost:6379/1',
#     CELERY_RESULT_BACKEND='redis://localhost:6379/1'
# )


# celery = Celery('app', broker='redis://localhost:6379/2')

app.config.update(
    CELERY_BROKER_URL='redis://localhost:6379/1',
    CELERY_RESULT_BACKEND='redis://localhost:6379/7'
)
celery = make_celery(app)
celery.conf.update(app.config)


# celery = Celery(
#         app.import_name,
#         broker=app.config['CELERY_BROKER_URL'],
#         backend=app.config['CELERY_RESULT_BACKEND']
#     )

@app.route('/')
def hello_world():
    # return 'Hello World!'
    print("耗时的请求")
    result = long_time_def.delay()
    print(result.result)
    result.wait()  # 65
    print(result.result)
    print("a")
    return "asdfas"
    # return redirect("/manage/login")


@app.route('/longtask', methods=['POST'])
def longtask():
    task = long_task.apply_async()
    return jsonify({'Location': url_for('taskstatus', task_id=task.id), "code": 202})


@app.route('/status/<task_id>')
def taskstatus(task_id):
    task = long_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


@celery.task(bind=True)
def long_task(self):
    """Background task that runs a long function with progress reports."""
    verb = ['Starting up', 'Booting', 'Repairing', 'Loading', 'Checking']
    adjective = ['master', 'radiant', 'silent', 'harmonic', 'fast']
    noun = ['solar array', 'particle reshaper', 'cosmic ray', 'orbiter', 'bit']
    message = ''
    total = random.randint(10, 50)
    for i in range(total):
        if not message or random.random() < 0.25:
            message = '{0} {1} {2}...'.format(random.choice(verb),
                                              random.choice(adjective),
                                              random.choice(noun))
        self.update_state(state='PROGRESS',
                          meta={'current': i, 'total': total,
                                'status': message})
        time.sleep(1)
    return {'current': 100, 'total': 100, 'status': 'Task completed!',
            'result': 42}


@celery.task()
def add_together(a, b):
    return a + b


@celery.task()
def long_time_def():
    for _ in range(10000):
        for j in range(10000):
            i = 1
    return 'hello'


# 后台登录
@app.route('/manage/login', methods=['POST', 'GET'])
def manage_login():
    if request.method == "GET":
        print("后台登录GET")
        user = {'username': 'Miguel'}
        return render_template('/manage/login.html', title='Home', user=user)
    if request.method == "POST":
        username = request.form.get('username')
        password = request.form.get('password')
        print("后台登录POST｛%s,%s｝" % (username, password))
        return redirect("/manage/home")


# 管理后台首页
@app.route('/manage/home', methods=['POST', 'GET'])
def manage_home():
    return render_template('/manage/index.html', username='Richie')


# 网站列表
@app.route('/manage/site_list', methods=['POST', 'GET'])
def manage_site_list():
    site_list = {}
    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:

            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT site.*,servers.name,servers.host,site_template.type,site_template.title as template_title FROM `site` left join `servers` on servers.id = site.server_id left join `site_template` on site_template.id = site.template_id LIMIT 0,10"
                cursor.execute(sql)
                site_list = cursor.fetchall()

                print(site_list)
    finally:
        connection.close()

    return render_template('/manage/site_list.html', title='Home', site_list=site_list)


# 添加网站
@app.route('/manage/site_add', methods=['POST', 'GET'])
def manage_site_add():
    if request.method == "GET":
        servers = {}
        templates = {}
        connection = pymysql.connect(host='120.76.232.162',
                                     user='root',
                                     password='lcn@123',
                                     db='site_group',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                # 查询服务器
                server_sql = "SELECT * FROM `servers` WHERE state = 1"
                cursor.execute(server_sql)
                servers = cursor.fetchall()
                # 查询模版
                template_sql = "SELECT * FROM `site_template` WHERE state = 1  and type=0"
                cursor.execute(template_sql)
                templates = cursor.fetchall()

        finally:
            connection.close()

        return render_template('/manage/site_add.html', title='Home', servers=servers, templates=templates)
    if request.method == "POST":
        title = request.form.get('title')
        server_id = request.form.get('server')
        keyword = request.form.get('keyword')
        domain = str(request.form.get('domain')).replace('http://', '').replace('https://', '')
        template = int(request.form.get('template'))
        description = request.form.get('description')
        web_path = domain.replace('.', '_')
        article_ids = request.form.get('content_id')

        print("添加网站POST｛%s,%s,%s,%s,%s｝" % (title, domain, template, keyword, description))
        # Connect to the database
        connection = pymysql.connect(host='120.76.232.162',
                                     user='root',
                                     password='lcn@123',
                                     db='site_group',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)

        try:
            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT * FROM `site` WHERE `domain`=%s LIMIT 1"
                cursor.execute(sql, domain)
                result = cursor.fetchone()
                print(result)
                if result is None:
                    # 添加站点
                    sql = "INSERT INTO `site` (`title`, `web_path`,`template_id`, `domain`,`keyword`, `description`,`state`, `create_time`,`article_ids`,`server_id`) VALUES (%s, %s, %s, %s, %s,%s,%s,%s,%s,%s)"
                    cursor.execute(sql, (
                        str(title), str(web_path), template, str(domain), str(keyword), str(description), 0,
                        int(time.time()), str(article_ids), str(server_id)))

                    # connection is not autocommit by default. So you must commit to save
                    # your changes.
                    connection.commit()

                else:
                    print("存在")
                    return redirect("/manage/site_add")

        finally:
            connection.close()

        return redirect("/manage/site_list")


# 批量添加网站
@app.route('/manage/site_add_batch', methods=['POST', 'GET'])
def manage_site_add_batch():
    if request.method == "GET":
        servers = {}
        connection = pymysql.connect(host='120.76.232.162',
                                     user='root',
                                     password='lcn@123',
                                     db='site_group',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                # 查询服务器
                server_sql = "SELECT * FROM `servers` WHERE state = 1"
                cursor.execute(server_sql)
                servers = cursor.fetchall()

        finally:
            connection.close()

        return render_template('/manage/site_add_batch.html', servers=servers)
    if request.method == "POST":
        server_id = request.form.get('server')
        domain = request.form.get('domain')
        title = request.form.get('title')
        keyword = request.form.get('keyword')
        description = request.form.get('description')
        domain_array = str(domain).splitlines()
        title_array = str(title).splitlines()
        keyword_array = str(keyword).splitlines()
        desc_array = str(description).splitlines()

        site_array = []

        for index, d_url in enumerate(domain_array):
            a = re_web_url(d_url)
            if a is not None:
                print(d_url)
                site = {
                    "domain": d_url,
                    "title": title_array[index],
                    "keyword": keyword_array[index],
                    "description": desc_array[index],
                    "server_id": server_id
                }
                site_array.append(site)
        # 插入数据库
        batch_add_site(site_array)
        return redirect("/manage/site_list")


# 生成html
@app.route("/manage/site_generate/<int:id>")
def manage_site_generate(id):
    site = {}
    # Connect to the database
    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:

            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT site.*,site_template.type as template_type,site_template.path as template_path FROM `site` left join `site_template` on site_template.id = site.template_id WHERE site.`id`=%s LIMIT 1"
                cursor.execute(sql, id)
                site = cursor.fetchone()
                print(site)
                if site is None:
                    print("网站不存在")
                    return redirect("/manage/site_list")
                elif site['template_type'] is None:
                    print("网站模版不存在")
                    return redirect("/manage/site_list")
                else:
                    article = {}
                    # 读取内容
                    if site['template_type'] == 0:
                        article_sql = "SELECT * FROM `article` WHERE `id`=%s LIMIT 1"
                        cursor.execute(article_sql, str(site['article_ids']).replace(',', ''))
                        article = cursor.fetchone()

                    print("开始生成网站：%s，%s" % (id, site['title']))

                    # 开始生成网站
                    PATH = os.path.dirname(os.path.abspath(__file__))
                    template_path = os.path.join(PATH, 'static/template/' + str(site['template_path']))

                    # 初始化模版
                    TEMPLATE_ENVIRONMENT = Environment(autoescape=False,
                                                       loader=FileSystemLoader(template_path),
                                                       trim_blocks=False)

                    # 创建网站生成的目录
                    targetDir = os.path.join(PATH, 'output/' + site['web_path'])
                    # 拷贝模版中的样式及图片文件
                    copyFiles(template_path, targetDir)
                    print("拷贝模版中的样式及图片文件成功")

                    if site['template_type'] == 0:
                        # 单页面网站生成html
                        # 读取html模版并赋值，
                        html = TEMPLATE_ENVIRONMENT.get_template('index.html').render(site=site, article=article)

                        # 生成网站
                        fname = targetDir + "/index.html"
                        with open(fname, 'w') as f:
                            # html.render()
                            f.write(html)

                        # 生成nginx conf
                        # conf = ''
                        confFile = open(os.path.join(PATH, 'static/template/nginx.conf'))
                        webConf = confFile.read().replace('{{domain}}', site['domain']).replace('{{webpath}}',
                                                                                                site['web_path'])
                        # print(webConf)
                        # 生成nginx配置文件
                        with open(targetDir + "/" + site['web_path'] + ".conf", 'w') as f:
                            f.write(webConf)

                    # 更新网站状态为：已生成
                    sql = "UPDATE site SET is_generated=1 WHERE id=" + str(id)
                    cursor.execute(sql)

                    # connection is not autocommit by default. So you must commit to save
                    # your changes.
                    connection.commit()

    finally:
        connection.close()

    return Response(json.dumps(site), mimetype='application/json')


# 生成html
@app.route("/manage/site_generate_batch")
def manage_site_generate_batch():
    if request.method == "GET":
        site = {}
        connection = pymysql.connect(host='120.76.232.162',
                                     user='root',
                                     password='lcn@123',
                                     db='site_group',
                                     charset='utf8mb4',
                                     cursorclass=pymysql.cursors.DictCursor)
        try:
            with connection.cursor() as cursor:
                # 查询服务器
                server_sql = "SELECT COUNT(0) AS count FROM `site` WHERE state = 0"
                cursor.execute(server_sql)
                site = cursor.fetchone()

        finally:
            connection.close()

        return render_template('/manage/site_generate_batch.html', site_count=site['count'])


# 启动批量生成后台运行
@app.route('/manage/site_generate_batch_start', methods=['POST'])
def manage_site_generate_batch_start():
    task = site_generate_task.apply_async()
    return jsonify({'Location': url_for('site_generate_status', task_id=task.id), "code": 202})


# 后台程序状态查询
@app.route('/manage/site_generate_status/<task_id>')
def site_generate_status(task_id):
    task = site_generate_task.AsyncResult(task_id)
    if task.state == 'PENDING':
        # job did not start yet
        response = {
            'state': task.state,
            'current': 0,
            'total': 1,
            'status': 'Pending...'
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'current': task.info.get('current', 0),
            'total': task.info.get('total', 1),
            'status': task.info.get('status', '')
        }
        if 'result' in task.info:
            response['result'] = task.info['result']
    else:
        # something went wrong in the background job
        response = {
            'state': task.state,
            'current': 1,
            'total': 1,
            'status': str(task.info),  # this is the exception raised
        }
    return jsonify(response)


# 批量生成html 后台程序
@celery.task(bind=True)
def site_generate_task(self):
    site_list = []
    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            sql = "SELECT site.*,site_template.type as template_type,site_template.path as template_path FROM `site` left join `site_template` on site_template.id = site.template_id WHERE site.`state`=0"
            cursor.execute(sql)
            site_list = cursor.fetchall()
            len(site_list)

            for index, site in enumerate(site_list):
                if site['article_ids'] is not None and site['template_type'] is not None:
                    # 有内容才生成
                    article = {}
                    # 读取内容
                    if site['template_type'] == 0:
                        article_sql = "SELECT * FROM `article` WHERE `id`=%s LIMIT 1"
                        cursor.execute(article_sql, str(site['article_ids']).replace(',', ''))
                        article = cursor.fetchone()
                        PATH = os.path.dirname(os.path.abspath(__file__))
                        generator(site, article, PATH)
                        # 更新网站状态为：已生成
                        sql = "UPDATE site SET is_generated=1 WHERE id=" + str(site['id'])
                        cursor.execute(sql)
                        connection.commit()

                self.update_state(state='PROGRESS',
                                  meta={'current': index, 'total': len(site_list),
                                        'status': "OK"})
                time.sleep(1)

    finally:
        connection.close()

    return {'current': len(site_list), 'total': len(site_list), 'status': 'Task completed!',
            'result': 42}


# 复制文件
def copyFiles(sourceDir, targetDir):
    # 将模版里的样式文件拷贝到网站目录
    for f in os.listdir(sourceDir):
        sourceF = os.path.join(sourceDir, f)
        targetF = os.path.join(targetDir, f)
        print("文件名：%s" % sourceF)
        if os.path.isfile(sourceF) and f != ".DS_Store" and f.find('.html') < 0:

            if not os.path.exists(targetDir):
                os.makedirs(targetDir)

            if not os.path.exists(targetF) or (
                    os.path.exists(targetF) and (os.path.getsize(targetF) != os.path.getsize(sourceF))):
                # 2进制文件   * l$ _  o- b2 ~" a

                open(targetF, "wb").write(open(sourceF, "rb").read())
                print(u"%s %s 复制完毕" % (time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), targetF))

        if os.path.isdir(sourceF):
            copyFiles(sourceF, targetF)


# 网站资讯内容弹窗
@app.route("/manage/site_content_iframe")
def manage_site_content_iframe():
    template_type = request.args.get('t', '2')
    print(template_type)
    content_list = {}

    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:

            with connection.cursor() as cursor:
                # Read a single record
                sql = "SELECT id,title FROM `article` LIMIT 0,10"
                cursor.execute(sql)
                content_list = cursor.fetchall()

                # print(site_list)
    finally:
        connection.close()

        # content_list.append(obj)

    return render_template('/manage/site_content_iframe.html', list=content_list, template=int(template_type))


# 发布网站
@app.route("/manage/site_publish/<int:id>")
def manage_site_publish(id):
    print("发布网站%s", str(id))
    site = {}
    # Connect to the database
    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            # Read a single record
            sql = "SELECT site.*,servers.id as serverId,servers.host,servers.port,servers.user_name,servers.user_pwd,servers.nginx_config_path,servers.web_site_path FROM `site` left join `servers` on servers.id=site.server_id WHERE site.`id`=%s LIMIT 1"
            cursor.execute(sql, id)
            site = cursor.fetchone()
            # print(site)
            if site is None:
                print("网站不存在")
                return redirect("/manage/site_list")
            elif site['serverId'] is None:
                print("服务器不存在")
                return redirect("/manage/site_list")
            else:
                print("开始发布%s" % site['title'])

                # remote_dir = "/var/www/%s/" % site['web_path']
                remote_dir = site['web_site_path'] + site['web_path']

                PATH = os.path.dirname(os.path.abspath(__file__))
                local_dir = os.path.join(PATH, 'output/%s' % site['web_path'])

                # 发布网站到服务器 （上传网站、上传nginx conf）
                sftp_put(remote_dir, local_dir, site['web_path'], site['host'], site['port'], site['user_name'],
                         site['user_pwd'])

                # 更新发布状态
                # 更新网站状态为：已生成
                sql = "UPDATE site SET is_released=1 WHERE id=" + str(id)
                cursor.execute(sql)
                connection.commit()

    finally:
        connection.close()

    # 更新网站状态为：已生成
    # sql = "UPDATE site SET is_generated=1 WHERE id=" + str(id)
    # cursor.execute(sql)
    #
    # # connection is not autocommit by default. So you must commit to save
    # # your changes.
    # connection.commit()

    site = {
        "t": "adsfs"
    }

    return Response(json.dumps(site), mimetype='application/json')


# sftp上传到服务器
def sftp_put(remote_dir, local_dir, site_id, server_host, server_port, user_name, user_pwd):
    # 连接服务器
    transport = paramiko.Transport((server_host, server_port))
    transport.connect(username=user_name, password=user_pwd)
    sftp = paramiko.SFTPClient.from_transport(transport)

    print('upload file start %s ' % datetime.datetime.now())

    # remote_dir = "/var/www/www_hwz_cc/"

    # PATH = os.path.dirname(os.path.abspath(__file__))
    # local_dir = os.path.join(PATH, 'output/www_hwz_cc')

    for root, dirs, files in os.walk(local_dir):
        print('[%s][%s][%s]' % (root, dirs, files))

        for filespath in files:
            local_file = os.path.join(root, filespath)
            print(11, '[%s][%s][%s][%s]' % (root, filespath, local_file, local_dir))

            a = local_file.replace(local_dir, '').replace('\\', '/').lstrip('/')

            print('01', a, '[%s]' % remote_dir)

            remote_file = os.path.join(remote_dir, a).replace('\\', '/')

            print(22, remote_file)
            try:
                sftp.put(local_file, remote_file)
            except Exception as e:

                sftp.mkdir(os.path.split(remote_file)[0])

                sftp.put(local_file, remote_file)

                print("66 upload %s to remote %s" % (local_file, remote_file))

        for name in dirs:

            local_path = os.path.join(root, name)

            print(0, local_path, local_dir)

            a = local_path.replace(local_dir, '').replace('\\', '/').lstrip('/')

            print(1, a)

            print(1, remote_dir)
            # remote_path = os.path.join(remote_dir, a).replace('\\', '/')

            remote_path = remote_dir + a

            print(33, remote_path)

            try:
                sftp.mkdir(remote_path)
                print(44, "mkdir path %s" % remote_path)
            except Exception as e:

                print(55, e)
    print('77,upload file success %s ' % datetime.datetime.now())
    # 上传conf文件到nginx/conf.d
    #
    #
    # # 将resutl.txt 上传至服务器 /tmp/result.txt
    sftp.put(local_dir + '/' + site_id + '.conf', '/etc/nginx/conf.d/' + site_id + '.conf')
    # # 将result.txt 下载到本地
    # sftp.get('/tmp/result.txt', '~/yours.txt')
    transport.close()


# 模版管理
@app.route("/manage/template_list")
def template_list():
    template_list = {}
    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `site_template` LIMIT 0,10"
            cursor.execute(sql)
            template_list = cursor.fetchall()

            # print(site_list)
    finally:
        connection.close()

    return render_template('/manage/template_list.html', list=template_list)


# 服务管理
@app.route("/manage/server_list")
def server_list():
    server_list = {}
    connection = pymysql.connect(host='120.76.232.162',
                                 user='root',
                                 password='lcn@123',
                                 db='site_group',
                                 charset='utf8mb4',
                                 cursorclass=pymysql.cursors.DictCursor)

    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM `servers` LIMIT 0,10"
            cursor.execute(sql)
            server_list = cursor.fetchall()

            # print(site_list)
    finally:
        connection.close()

    return render_template('/manage/server_list.html', list=server_list)


if __name__ == '__main__':
    # app.run(debug=True, threaded=True)
    app.run(debug=True, threaded=True)
