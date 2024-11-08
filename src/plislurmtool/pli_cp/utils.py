def progress_bar(percent, length=50):
    """
    Progress bar for displaying remaining quora
    """
    pbar = "█" * min(length, int(percent // (1 / length)))
    pbar += "░" * (length - len(pbar))
    pbar += f"  {100 * percent:.2f}%"
    return pbar


def email_hpgres_cap_warning(user, message, active_jobs):
    header = f"[Della-PLI-CP] {user} High Priority GPU Quota Exceeded"

    body = f"Dear user {user},\n\nOur monitoring system detected that you have exceeded the designated quota for high priority GPU (pli-pc). Please cancel jobs launched on pli-cp and use the general partition pli-c instead.\nWe have a 1-day grace period for the quota. Jobs launched tomorrow will be scanceled directly.\n\nThank you for your cooperation.\n\n{message}\n"

    for job in active_jobs:
        body += f"Job ID: {job['job_id']}: \t {job['job_name']}\n"
    print(header)

    # TODO: Email the user


def email_hpgres_cap_canceling(user, message, active_jobs):
    header = f"[Della-PLI-CP] {user} High Priority GPU Quota Exceeded, Jobs Canceled!"

    body = f"Dear user {user},\n\nOur monitoring system detected that you have exceeded the designated quota for high priority GPU (pli-pc). We have canceled the following jobs. Please use the pli-c partition instead. Thanks for your cooperation\n\n{message}\n"

    if len(active_jobs) > 0:
        body += "Canceled Jobs:\n"
    for job in active_jobs:
        body += f"Job ID: {job['job_id']}: \t {job['job_name']}\n"
    print(header)

    # TODO: Email the user


def cancel_job(job_id):
    print(f"Canceling job {job_id}")

    # TODO: Cancel job
    # os.system(f"scancel {job_id}")
