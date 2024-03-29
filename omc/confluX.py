from string import Template
from omc import encolored
import os
import requests
import re

# Rewrite using yaml.parser as soon as possible.


class Proxy:
    '''self represents the instance of the class.'''

    def __init__(self, exec_dir, output_path, schtype, rules, head, storage,
                 template_path, re_exclude):
        self.exec_dir = exec_dir
        self.storage = storage
        self.schemetype = schtype
        self.rules_path = rules
        self.head_path = head
        self.output_path = output_path
        self._All_exclude = re_exclude
        self.script = ""
        self.template_path = template_path
        names = self.__dict__
        for x in ['proxy_groups_selector',
                  'proxy_groups_provider',
                  'proxy_groups_proxies',
                  'proxy_providers',
                  'urltest']:
            template_file = template_path + '/' + x
            if os.path.isfile(template_file):
                y = open(template_file).read()
            else:
                encolored.Error(f"template: {x} not exist.", exit())

            names[x] = Template(y)

        self.urltest = self.urltest.substitute(
            url='http://www.gstatic.com/generate_204', interval=300, tolerance=10)

    def get_filename(self, _dir):

        name_path, region_icons, hidden_path = dict(), dict(), dict()
        # recognize sub dirs as well.
        for root, dirs, names in os.walk(_dir):
            for name in names:
                if name[0] == '.':
                    hidden_path[name] = os.path.join(
                        root, name).replace('\\', '/')
                elif root.split('/')[-1] == 'region':
                    region_icons[name] = os.path.join(
                        root, name).replace('\\', '/')
                else:
                    # fix NT "\".
                    name_path[name] = os.path.join(
                        root, name).replace('\\', '/')
        return name_path, region_icons, hidden_path

    def get_template(self):
        rules = self.rules_path
        head = self.head_path
        template_path = self.template_path
        if 'http' in rules:
            self.rules = requests.get(rules).content.decode('utf-8').strip()
        else:
            self.rules = open(rules + '.download', 'r').read().strip()
        if 'http' in head:
            self.head = requests.get(head).content.decode('utf-8').strip()
        else:
            self.head = open(head, 'r').read().strip()
        if os.path.isfile(template_path + '/' + 'rules.yml'):
            self.rules = self.rules.replace('rules:\n', open(
                template_path + '/' + 'rules.yml').read() + '\n')
        if os.path.isfile(template_path + '/' + 'script.yml'):
            self.script += open(template_path + '/' + 'script.yml').read()

    def gen_proxy_providers(self):
        ret = ""
        for x, y in self.proxy_path.items():
            ret += self.proxy_providers.substitute(
                name=x, location=self.storage + '/' + y)
        return ret

    def gen_all_proxies(self):

        def proxies_scheme(typ='common'):
            ret = ""

            if self.schemetype != 'both':
                proxy_path = self.proxy_path
            elif typ == 'All':
                proxy_path = self.icon_path
            elif typ == 'common':
                proxy_path = self.proxy_path
            else:
                exit('type must be common or All.')
            for x in proxy_path:
                if typ == 'All' and re.search(self._All_exclude, x, re.IGNORECASE):
                    pass
                else:
                    ret += f"\t- {x}\n"
            return ret.strip('\n')

        def gen_rules():
            # Fix needed for SCRIPT, using yaml.parser is preferred.
            sets = re.findall('\n- .*,.*,?.*', self.rules)
            rules_proxies = []
            for x in sets:
                # structure: RULE-SET,rules,proxy-group
                rule_name = re.split(',', x)[-1]
                if rule_name not in rules_proxies:
                    rules_proxies.append(rule_name)
            ret = ""
            rules_proxies.sort()
            for x in rules_proxies:
                if x in ['AdBlock', 'Advertising', 'Hijacking', 'Privacy', 'Reject', 'QUIC']:
                    # REJECT by default. without proxies.
                    ret += self.proxy_groups_selector.substitute(
                        name=x, type='select', proxies="\t- REJECT\n\t- DIRECT\n\t- Proxy")
                elif x in ['DIRECT', 'REJECT']:
                    continue  # Pass Bulit-in.
                elif x == 'Proxy':
                    ret += self.proxy_groups_selector.substitute(
                        name=x, type='select', proxies='\t- All\n' + proxies_scheme()+'\n\t- DIRECT')
                elif x in ['Domestic', 'China', 'StreamingSE', 'Asian TV', 'Google FCM', 'UDP', 'Other Ports', 'BitTorrent']:
                    # DIRECT by default. with proxies.
                    ret += self.proxy_groups_selector.substitute(
                        name=x, type='select', proxies='\t- DIRECT\n\t- Proxy\n' + proxies_scheme())
                else:
                    ret += self.proxy_groups_selector.substitute(
                        name=x, type='select', proxies='\t- Proxy\n' + proxies_scheme() + '\n\t- DIRECT')
            return ret
        return self.proxy_groups_provider.substitute(name='All', type='url-test', uses=proxies_scheme('All'), urltest=self.urltest) + gen_rules()

    def gen_each_proxies(self):
        ret = ""
        for x in self.proxy_path:
            ret += self.proxy_groups_provider.substitute(
                name=x, type='url-test', uses=f"\t- {x}", urltest=self.urltest)
        return ret

    def arranger(self):
        self.named_path, self.icon_path, self.hidden_path = self.get_filename(
            self.exec_dir)
        self.get_template()
        if self.schemetype == 'icon':
            self.proxy_path = self.icon_path
        elif self.schemetype == 'named':
            self.proxy_path = self.named_path
        elif self.schemetype == 'both':
            self.proxy_path = self.named_path | self.icon_path
        elif self.schemetype == 'merged':
            self.proxy_path = self.hidden_path
        file = f"""
{self.head}

proxy-providers:
{self.gen_proxy_providers()}
proxy-groups:
{self.gen_all_proxies()}
{self.gen_each_proxies()}
{self.script}

{self.rules}
"""
        file = file.replace('\t', '  ')  # YAML dont support Tabulator key.
        with open(self.output_path, 'w') as f:
            f.write(file.strip())


class QuanX:
    def __init__(self, exec_dir, output_path, storage, template_path, re_exclude):
        self.storage = storage
        self.output_path = output_path
        self._All_exclude = re_exclude
        self.name_path = [(name, os.path.join(root, name).replace('\\', '/'))
                          for root, dirs, names in os.walk(exec_dir) for name in names]
        self.template_path = template_path

    def arranger(self):
        content = ""
        for name, path in self.name_path:
            if not re.search(self._All_exclude, name, re.IGNORECASE):
                enable_proxies = "true"
            else:
                enable_proxies = "false"
            content += ";{0}, tag={1}, as-policy=static, enabled={2}\n".format(
                self.storage + '/' + path, name, enable_proxies)
        content = content.strip()
        if 'http' in self.template_path:
            conf_content = requests.get(
                self.template_path).content.decode('utf-8').format(content)
        else:
            with open(self.template_path) as tmp:
                conf_content = tmp.read().format(content)
        with open(self.output_path, 'w') as conf:
            conf.write(conf_content)
