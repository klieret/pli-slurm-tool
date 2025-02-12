def progress_bar(percent, length=50):
    """
    Progress bar for displaying remaining quora
    """
    pbar = "█" * min(length, int(percent // (1 / length)))
    pbar += "░" * (length - len(pbar))
    pbar += f"  {100 * percent:.3f}%"
    return pbar


def email_hpgres_cap_warning(user, message, active_jobs, yag, account: str = None):

    if not account:
        header = f"[Della-PLI-CP] {user} High Priority GPU Quota Exceeded"
        body = f"Dear user {user},\n\nOur monitoring system detected that you have exceeded the designated quota for high priority GPU (pli-pc). Please cancel jobs launched on pli-cp and use the general partition pli-c instead.\nWe have a 1-day grace period for the quota. Jobs launched tomorrow will be scanceled directly.\n\nThank you for your cooperation.\n\n{message}\n"
    else:
        header = f"[Della-PLI-LC] GPU Quota Exceeded for account {account}"
        body = f"Dear user {user},\n\nOur monitoring system detected that the account you are part of ({account}) has exceeded the designated quota on PLI-LC. Please cancel jobs launched with the associated account on pli-lc.\nWe have a 1-day grace period for the quota. Jobs launched tomorrow will be scanceled directly.\n\nThank you for your cooperation.\n\n{message}\n"

    for job in active_jobs:
        body += f"Job ID: {job['job_id']}: \t {job['job_name']}\n"
    print(header)

    try:
        yag.send(f"{user}@princeton.edu", header, body)
    except Exception as e:
        print(f"Error while sending email to {user}@princeton.edu: {str(e)}")

def email_hpgres_cap_canceling(user, message, active_jobs, yag, account: str = None):

    if not account:
        header = f"[Della-PLI-CP] {user} High Priority GPU Quota Exceeded, Jobs Canceled!"
        body = f"Dear user {user},\n\nOur monitoring system detected that you have exceeded the designated quota for high priority GPU (pli-pc). We have canceled the following jobs. Please use the pli-c partition instead. Thanks for your cooperation\n\n{message}\n"

    else:
        header = f"[Della-PLI-LC] GPU Quota Exceeded for account {account}, Jobs Canceled!"
        body = f"Dear user {user},\n\nOur monitoring system detected that the account you are part of ({account}) has exceeded the designated quota on PLI-LC. We have canceled the following jobs. Thanks for your cooperation\n\n{message}\n"
       
    if len(active_jobs) > 0:
        body += "Canceled Jobs:\n"
    for job in active_jobs:
        body += f"Job ID: {job['job_id']}: \t {job['job_name']}\n"
    print(header)

    try:
        yag.send(f"{user}@princeton.edu", header, body)
    except Exception as e:
        print(f"Error while sending email to {user}@princeton.edu: {str(e)}")


def cancel_job(job_id):
    print(f"Canceling job {job_id}")

    # TODO: Cancel job
    # os.system(f"scancel {job_id}")
