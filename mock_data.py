from flask import Flask, Response
import json

app = Flask(__name__)


@app.route('/hosts', methods=['GET'])
def get_hosts():
    hosts = {'hosts': ['10.222.16.1', '10.222.16.15']}
    return Response(json.dumps(hosts), mimetype='application/json')


@app.route('/tags', methods=['GET'])
def get_tags():
    tags = {'succ': 0, 'tag_list': {'10.222.16.1': 'cluster,hadoop,cluster_hadoop_hdfs_nn',
                                    '10.222.16.15': 'cluster,hadoopm,cluster_hadoop_hdfs_dn'}}
    return Response(json.dumps(tags), mimetype='application/json')


if __name__ == '__main__':
    app.run(host='localhost', port=5001, debug=True)
