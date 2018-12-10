#!/usr/bin/env python
import datetime
import sys
import logging
from pprint import pprint
from collections import defaultdict, OrderedDict

import jira
import argparse

from testrail import TestRail
from testrail.test import Test
# from testrail_api import APIClient
from functools32 import lru_cache

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)
LOG = logging.getLogger(__name__)


def run_cli():
    cli = argparse.ArgumentParser(
        prog="Report generator",
        description="Command line tool for generate summary report")

    commands = cli.add_subparsers(
        title="Operation commands",
        dest="command")

    cli_process = commands.add_parser(
        "create-report",
        help="Create summary report",
        description="Create summary report")
    cli_process_link = commands.add_parser(
        "mark-fails",
        help="Extract linked bugs from previous reports",
        description="Extract linked bugs from previous reports"
                    " and mark current")
    cli_process.add_argument(
        "-T", "--testrail-host", dest="testrail_host",
        required=True,
        help="TestRail hostname")
    cli_process.add_argument(
        "-U", "--testrail-user", dest="testrail_user",
        required=True,
        help="TestRail user email")
    cli_process.add_argument(
        "-K", "--testrail-user-key", dest="testrail_user_key",
        required=True,
        help="TestRail user key")
    cli_process.add_argument(
        "-R", "--testrail-plan", dest="testrail_plan",
        required=True,
        help="TestRail test plan for analize")
    cli_process.add_argument(
        "-P", "--testrail-project", dest="testrail_project",
        required=True,
        help="TestRail project name")
    cli_process.add_argument(
        "--testrail-only-run", dest="testrail_only_run",
        help="Analize only one run in selected plan")
    cli_process.add_argument(
        "--out-type", dest="out_type", choices=["text", "html", 'md', 'none'],
        default='none',
        help="Select output format for report table. "
             "By default print nothing (none).")
    cli_process.add_argument(
        "--sort-by", dest="sort_by", default='fails',
        choices=["fails", "blocks", 'project', 'priority', 'status'],
        help="Select sorting column. By deafult table sort by fails")
    cli_process.add_argument(
        "--push-to-testrail", dest="push_report_flag", action="store_true",
        default=False,
        help="Save report in plan description")
    cli_process.add_argument(
        "-j", "--jira-host", dest="jira_host",
        required=True,
        help="JIRA hostname")
    cli_process.add_argument(
        "-u", "--jira-user", dest="jira_user_id",
        required=True,
        help="JIRA username")
    cli_process.add_argument(
        "-p", "--jira-password", dest="jira_user_password",
        required=True,
        help="JIRA user password")

    # link fail bugs parameters
    cli_process_link.add_argument(
        "-T", "--testrail-host", dest="testrail_host",
        required=True,
        help="TestRail hostname")
    cli_process_link.add_argument(
        "-U", "--testrail-user", dest="testrail_user",
        required=True,
        help="TestRail user email")
    cli_process_link.add_argument(
        "-K", "--testrail-user-key", dest="testrail_user_key",
        required=True,
        help="TestRail user key")
    cli_process_link.add_argument(
        "-R", "--testrail-plan", dest="testrail_plan",
        required=True,
        help="TestRail test plan for analize")
    cli_process_link.add_argument(
        "-M", "--testrail-marked-plan", dest="testrail_marked_plan",
        required=False,
        help="TestRail test plan for parse")
    cli_process_link.add_argument(
        "-P", "--testrail-project", dest="testrail_project",
        required=True,
        help="TestRail project name")
    cli_process_link.add_argument(
        "--testrail-only-run", dest="testrail_only_run",
        help="Analize only one run in selected plan")
    cli_process_link.add_argument(
        "--search-coverage", dest="search_coverage", choices=["run", "plan"],
        default='plan',
        help="Search marked bugs by run or by plan. ")
    cli_process_link.add_argument(
        "--date-period-count", dest="date_period_count",
        default=7,
        help="Count days period for search bug links diapason")
    cli_process_link.add_argument(
        "--push-to-testrail", dest="update_report_flag", action="store_true",
        default=False,
        help="Save report in plan description")
    # cli_process_link.add_argument(
    #     "-j", "--jira-host", dest="jira_host",
    #     required=True,
    #     help="JIRA hostname")
    # cli_process_link.add_argument(
    #     "-u", "--jira-user", dest="jira_user_id",
    #     required=True,
    #     help="JIRA username")
    # cli_process_link.add_argument(
    #     "-p", "--jira-password", dest="jira_user_password",
    #     required=True,
    #     help="JIRA user password")

    if len(sys.argv) == 1:
        cli.print_help()
        sys.exit(1)

    return cli.parse_args()


def get_runs(t_client, plan_name, run_name):
    LOG.info("Get runs from plan - {}".format(plan_name))
    ret = []
    plan = t_client.plan(plan_name)
    if plan:
        for e in plan.entries:
            for r in e.runs:
                LOG.info("Run {} #{}".format(r.name, r.id))
                if run_name is not None and r.name != run_name:
                    continue
                ret.append(r)
    else:
        LOG.warning("Plan {} is empty".format(plan_name))
    return ret


def get_all_results(t_client, list_of_runs):
    ret = []
    for run in list_of_runs:
        ret.extend(get_results(t_client, run))
    return ret


def get_all_failed_results(t_client, list_of_runs, result_type):
    ret = []
    for run in list_of_runs:
        ret.extend(get_failed_results(t_client, run, result_type))
    return ret


@lru_cache()
def fetch_test(api, test_id, run_id):
    return Test(api.test_with_id(test_id, run_id))


def get_results(t_client, run):
    LOG.info("Get results for run - {}".format(run.name))
    results = t_client.results(run)
    ret = [(run.id, r) for r in results
           if r.raw_data()['status_id'] is not None and
           r.raw_data()['defects'] is not None]
    for r in ret:
        run_id, result = r
        test = fetch_test(result.api, result.raw_data()['test_id'], run_id)
        LOG.info("Test {} - {} - {}".format(test.title, result.status.name,
                                            ','.join(result.defects)))
    return ret


def get_failed_results(t_client, run, result_type):
    LOG.info("Get results for run - {}".format(run.name))
    results = t_client.results(run)
    results_with_test = []
    if result_type is None:
        ret = [(run, r) for r in results
               if r.raw_data()['status_id'] is not None and
               r.raw_data()['defects'] is not None]
    else:
        ret = [(run, r) for r in results
               if r.raw_data()['status_id'] is int(result_type) and
               r.raw_data()['defects'] is None]
    for r in ret:
        run, result = r
        test = fetch_test(result.api, result.raw_data()['test_id'], run.id)
        LOG.info("Test {} - {} - {}".format(test.title, result.status.name,
                                            ','.join(result.defects)))
        results_with_test.append([run, result, test])
    return results_with_test


def mark_failed_results(t_cl, marked_res, failed_res, s_cov):
    LOG.info("Extract marked tests and attach to failed")
    ret = []

    def generate_results(t_c, tst, m_d, m_r):
        tmp_result = t_c.result()
        tmp_result.test = tst
        tmp_result.defects.append(m_d)
        tmp_result.status = m_r.status
        tmp_result.comment = "Generated by script"
        return tmp_result

    for run, result, test in failed_res:
        for m_run, m_result, m_test in marked_res:
            if s_cov == 'run' and test.title == m_test.title:
                LOG.info("MARKED FOUND {} - {}" .format(test.title,
                         m_result.defects[0]))
                ret.append([generate_results(t_cl, test, m_result.defects,
                                             m_result), run.id])
            elif s_cov == 'plan' and run.name == m_run.name \
                    and test.title == m_test.title:
                LOG.info("MARKED FOUND {} - {}" .format(test.title,
                         m_result.defects[0]))
                ret.append([generate_results(t_cl, test, m_result.defects,
                                             m_result), run.id])
    return ret


@lru_cache()
def get_defect_info(j_client, defect):
    LOG.info("Get info about issue {}".format(defect))
    try:
        issue = j_client.issue(defect)
    except jira.exceptions.JIRAError as e:
        if e.status_code == 404:
            LOG.error("Defect {} wasn't found in Jira".format(defect))
            return {
                'id': defect,
                'title': "Title for #{} not found".format(defect),
                'project': "Not found",
                'priority': "Not found",
                'status': "Not found",
                'url': "Not found"
            }
        else:
            raise
    return {
        'id': issue.key,
        'title': issue.fields.summary,
        'project': issue.fields.project.key,
        'priority': issue.fields.priority.name,
        'status': issue.fields.status.name,
        'url': issue.permalink()
    }


def get_defects_table(jira_client, list_of_results, sort_by):
    LOG.info("Collect report table")
    table = defaultdict(dict)
    for run_id, result in list_of_results:
        for defect in result.defects:
            if defect not in table:
                info = get_defect_info(jira_client, defect)

                table[defect].update(info)
                table[defect]['results'] = set([(run_id, result)])
                if result.status.name.lower() == 'blocked':
                    table[defect]['blocks'] = 1
                    table[defect]['fails'] = 0
                else:
                    table[defect]['fails'] = 1
                    table[defect]['blocks'] = 0
            else:
                table[defect]['results'].add((run_id, result))
                if result.status.name.lower() == 'blocked':
                    table[defect]['blocks'] += 1
                else:
                    table[defect]['fails'] += 1
    return OrderedDict(
        sorted(table.items(), key=lambda i: i[1][sort_by], reverse=True))


def get_text_table(table):
    LOG.info("Generation text table")
    lines = []
    line = ("{fails:^5} | {blocks:^5} | {project:^10} | {priority:^15} | "
            "{status:^15} | {bug:^100} | {tests} ")

    def title_uid(r):
        run_id, result = r
        test = fetch_test(result.api, result.raw_data()['test_id'], run_id)
        return {
            "title": test.title,
            "uid": test.id}

    def list_of_defect_tests(results):
        ret = ["[{title} #{uid}]".format(**title_uid(r)) for
               r in results]
        return ' '.join(ret)

    lines.append(line.format(fails='FAILS', blocks='BLOCKS', project="PROJECT",
                             priority="PRIORITY", status="STATUS", bug="BUG",
                             tests="TESTS"))
    for k in table:
        one = table[k]
        data = {
            "fails": one['fails'],
            "blocks": one['blocks'],
            "project": one['project'],
            "priority": one['priority'],
            "status": one['status'],
            "bug": "{uid} {title}".format(uid=one['id'], title=one['title']),
            "tests": list_of_defect_tests(one['results'])
        }
        lines.append(line.format(**data))
    return '\n'.join(lines)


def get_md_table(table):
    LOG.info("Generation MD table")
    lines = []
    line = ("||{fails} | {blocks} | {project} | {priority} | "
            "{status} | {bug} | {tests} ")

    def title_uid_link(r):
        run_id, result = r
        test = fetch_test(result.api, result.raw_data()['test_id'], run_id)

        return {
            "title": test.title.replace('[', '{').replace(']', '}'),
            "uid": test.id,
            "link": "{url}/index.php?/tests/view/{uid}".format(
                url=test.api._conf()['url'], uid=test.id)
        }

    def list_of_defect_tests(results):
        ret = ["<[{title} #{uid}]({link})>".format(**title_uid_link(r))
               for r in results]
        return ' '.join(ret)

    lines.append(line.format(fails='|:FAILS', blocks=':BLOCKS',
                             project=":PROJECT", priority=":PRIORITY",
                             status=":STATUS", bug=":BUG", tests=":TESTS"))
    for k in table:
        one = table[k]
        data = {
            "fails": one['fails'],
            "blocks": one['blocks'],
            "project": one['project'],
            "priority": one['priority'],
            "status": one['status'],
            "bug": "[{uid} {title}]({url})".format(
                uid=one['id'],
                title=one['title'].replace('[', '{').replace(']', '}'),
                url=one['url']),
            "tests": list_of_defect_tests(one['results'])
        }
        lines.append(line.format(**data))
    return '\n'.join(lines)


def get_html_table(table):
    LOG.info("Generation HTML table")
    html = "<table>{lines}</table>"
    lines = []
    line = ("<tr><th>{fails:^5}</th><th>{blocks:^5}</th><th>{project:^10}</th>"
            "<th>{priority:^15}</th>"
            "<th>{status:^15}</th><th>{bug:^100}</th><th>{tests}</th></tr>")
    lines.append(line.format(fails='FAILS', blocks='BLOCKS', project="PROJECT",
                             priority="PRIORITY", status="STATUS", bug="BUG",
                             tests="TESTS"))

    def title_uid_link(r):
        run_id, result = r
        test = fetch_test(result.api, result.raw_data()['test_id'], run_id)

        return {
            "title": test.title,
            "uid": test.id,
            "link": "{url}/index.php?/tests/view/{uid}".format(
                url=test.api._conf()['url'], uid=test.id)
        }

    def list_of_defect_tests(results):
        ret = ["<a href='{link}'>{title} #{uid}</a>".format(
            **title_uid_link(r)) for r in results]
        return ' '.join(ret)

    for k in table:
        one = table[k]
        data = {
            "fails": one['fails'],
            "blocks": one['blocks'],
            "project": one['project'],
            "priority": one['priority'],
            "status": one['status'],
            "bug": "<a href='{url}'>{uid} {title}</a>".format(
                uid=one['id'], title=one['title'], url=one['url']),
            "tests": list_of_defect_tests(one['results'])
        }
        lines.append(line.format(**data))
    return html.format(lines=''.join(lines))


def out_table(out_type, table):
    if out_type == 'none':
        return
    elif out_type == 'html':
        print(get_html_table(table))
    elif out_type == 'md':
        print(get_md_table(table))
    else:
        print(get_text_table(table))


def push_report(t_client, plan_name, table):
    LOG.info("Push report table into plan - {}".format(plan_name))
    text = "Bugs Statistics (generated on {date})\n" \
           "=======================================================\n" \
           "{table}".format(
            date=datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"),
            table=get_md_table(table))
    plan = t_client.plan(plan_name)
    if plan:
        plan.description = text
        plan.api._post(
            'update_plan/{}'.format(plan.id),
            {
                'name': plan.name,
                'description': plan.description,
                'milestone_id': plan.milestone.id
            })


def update_report(t_client, plan_name, tests_table):
    LOG.info("Push report table into plan - {}".format(plan_name))
    # text = "Bugs Statistics (generated on {date})\n" \
    #        "=======================================================\n" \
    #        .format(
    #         date=datetime.datetime.now().strftime("%a %b %d %H:%M:%S %Y"))
    plan = t_client.plan(plan_name)
    if plan:
        for r_test, run in tests_table:
            pprint(run)
            pprint(r_test.defects)
            # t_client.add(r_test)


def create_report(**kwargs):
    j_host = kwargs.get('jira_host')
    j_user = kwargs.get('jira_user_id')
    j_user_pwd = kwargs.get('jira_user_password')
    t_host = kwargs.get('testrail_host')
    t_user = kwargs.get('testrail_user')
    t_user_key = kwargs.get('testrail_user_key')
    t_plan = kwargs.get('testrail_plan')
    t_project = kwargs.get('testrail_project')
    t_a_run = kwargs.get('testrail_only_run')
    o_type = kwargs.get('out_type')
    push_report_flag = kwargs.get('push_report_flag')
    sort_by = kwargs.get('sort_by')

    t_client = TestRail(email=t_user, key=t_user_key, url=t_host)
    t_client.set_project_id(t_client.project(t_project).id)

    j_client = jira.JIRA(j_host, basic_auth=(j_user, j_user_pwd))

    runs = get_runs(t_client, t_plan, t_a_run)
    results = get_all_results(t_client, runs)
    table = get_defects_table(j_client, results, sort_by)
    out_table(o_type, table)
    if push_report_flag:
        push_report(t_client, t_plan, table)


def mark_fails(**kwargs):
    t_host = kwargs.get('testrail_host')
    t_user = kwargs.get('testrail_user')
    t_user_key = kwargs.get('testrail_user_key')
    t_plan = kwargs.get('testrail_plan')
    t_m_plan = kwargs.get('testrail_marked_plan')
    t_project = kwargs.get('testrail_project')
    t_a_run = kwargs.get('testrail_only_run')
    search_coverage = kwargs.get('search_coverage')
    update_report_flag = kwargs.get('update_report_flag')

    t_client = TestRail(email=t_user, key=t_user_key, url=t_host)
    t_client.set_project_id(t_client.project(t_project).id)

    if t_a_run is not None and search_coverage == 'run':
        marked_runs = get_runs(t_client, t_m_plan, t_a_run)
    else:
        marked_runs = get_runs(t_client, t_m_plan, None)
    runs = get_runs(t_client, t_plan, t_a_run)
    marked_results = get_all_failed_results(t_client, marked_runs, None)
    failed_results = get_all_failed_results(t_client, runs, '5')  # 5-failed

    tests_to_update = mark_failed_results(t_client, marked_results,
                                          failed_results, search_coverage)

    if update_report_flag:
        update_report(t_client, t_plan, tests_to_update)


COMMAND_MAP = {
    'create-report': create_report,
    'mark-fails': mark_fails
}


def main():
    args = run_cli()
    COMMAND_MAP[args.command](**vars(args))


if __name__ == '__main__':
    main()
