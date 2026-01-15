from django.shortcuts import redirect, render
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers import pipeline as transformer_pipeline
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from random_word import RandomWords
import random
import math
import torch
import itertools
from .forms import InputForm
from django.http.response import HttpResponseRedirect
import string
from .models import *
import json
import os
import wordninja
from datetime import datetime
from axes.models import AccessAttempt
from django.db.models import OuterRef, Subquery, Sum, Case, When, Value, BooleanField
from axes.handlers.base import AxesHandler

PROLIFIC_CODE = "NONE"

handler = AxesHandler()

def custom404(request, *args, **kwargs):
    return homepage(request)
    
def _my_json_error_response(message, status=200):
  response_json = '{ "error": "' + message + '" }'
  return HttpResponse(response_json, content_type='application/json', status=status)

# https://pypi.org/project/pyleetspeak/
def undo_leetspeak(pwd):
    prompt = f'Is the passphrase "{pwd}" written in leetspeak? Respond in one word, just "yes" or "no".'
    res = generate(prompt, temp=0.01, big=True)
    if "yes" in res.lower():
        prompt = f'Remove the leetspeak from this password, when appropriate: "{pwd}". Return the password, and nothing else.'
        v = generate(prompt, temp=0.01, big=True)
        if "I can" not in v: return v

    return pwd

def create_new_pwd_and_segments(user, pwd):

    custom_user = customUser()
    custom_user.uname = user.username

    custom_user.group = 1
    custom_user.stage = 2
    custom_user.substage = 1

    custom_user.last_access = datetime.now()

    custom_user.user = user
    custom_user.old_pwd = pwd
    custom_user.perm_suggestions = []
    custom_user.gen_suggestions = []


    custom_user.original_old_segments       = []
    custom_user.original_old_explanations   = []
    custom_user.original_new_segments       = []
    custom_user.original_new_explanations   = []
    
    custom_user.save()


def lockout(request, credentials, *args, **kwargs):

    return redirect(f'https://app.prolific.com/submissions/complete?cc={PROLIFIC_CODE}')

    url = f'https://app.prolific.com/submissions/complete?cc={PROLIFIC_CODE}'
    return render(request, 'pwd_web/lockout.html', context={'url': url, 'code': PROLIFIC_CODE})


def login_with_id(request, prolific_id="", login_case=1, error_msg=""):
    context = {
        "prolific_id": prolific_id,
        "login_case":login_case,
        "error_msg":error_msg
    }
    if login_case == 1 or login_case == "1":
        context["current_info"] = "Thank you for creating an account. Please log in to proceed."
    elif login_case == 2 or login_case == "2":
        context["current_info"] = "Please log in to participate. Use your Prolific ID and the password you created for this site."
    elif login_case == 3 or login_case == "3":
        context["current_info"] = "Please log back in to ensure that you remember your new password."
    elif login_case == 4 or login_case == "4":
        context["current_info"] = "Please log in to participate. Use your Prolific ID and the replacement password you created for this site last time."
    else:
        context["current_info"] = "Please log in to participate. Use your Prolific ID and the password you created for this site."

    # login 1 - after registering, stage 1
    # login 2 - stage 2, before changing pwd
    # login 3 - stage 2, after changing pwd
    # login 4+ - stage 3

    return render(request, 'pwd_web/login.html', context)

def login_page(request):
    if request.method == "POST" and "prolific_id" in request.POST and "stage" in request.POST: 
        if request.POST["stage"] == "2":
            return login_with_id(request, request.POST["prolific_id"], login_case=2)
        elif request.POST["stage"] == "3":
            return login_with_id(request, request.POST["prolific_id"], login_case=4)
    return login_with_id(request, "")

def intro(request):
    if "PROLIFIC_PID" in request.GET:
        prolific_id = request.GET["PROLIFIC_PID"]
    else:
        prolific_id = ""
    return intro_with_id(request, prolific_id=prolific_id)

def stage_intro(request):
    if "PROLIFIC_PID" in request.GET:
        prolific_id = request.GET["PROLIFIC_PID"]
    else:
        prolific_id = ""
    return stage_intro_with_id(request, prolific_id=prolific_id)
    
def stage_intro_with_id(request, prolific_id):
    return render(request, 'pwd_web/stage_intro.html', {"prolific_id": prolific_id})

def intro_with_id(request, prolific_id):
    return render(request, 'pwd_web/intro.html', {"prolific_id": prolific_id})

def consent(request):
    return render(request, 'pwd_web/consent_form.html')

def intro2(request):
    prolific_id = ""
    group = "1"
    if request.method == "GET":
        if "PROLIFIC_PID" in request.GET: prolific_id = request.GET["PROLIFIC_PID"]
        else: prolific_id = ""
        if "group" in request.GET: group = request.GET["group"]
        else: group = "1"

    return intro2_with_id(request, prolific_id=prolific_id, group=group)

def intro2_with_id(request, prolific_id, group):
    if group == "0": cost = 1
    else: cost = 3
    return render(request, 'pwd_web/intro2.html', {"prolific_id": prolific_id, "cost": cost})

def intro3(request):
    return intro3_with_id(request, prolific_id="")

def intro3_with_id(request, prolific_id):
    return render(request, 'pwd_web/intro3.html', {"prolific_id": prolific_id})

def register_with_id(request, prolific_id):
    return render(request, 'pwd_web/register.html', {"prolific_id": prolific_id})

def register_page(request):

    if request.method == "POST" and "prolific_id" in request.POST: return register_with_id(request, request.POST["prolific_id"])
    return register_with_id(request, "")


def get_segmentation_for_all():
    for custom_user in customUser.objects.all():
        user = custom_user.user
        if custom_user.group == 1:
            pwd = custom_user.old_pwd

            segments_query = list(segmentObject.objects.filter(custom_user=custom_user))

            if len(segments_query) == 0:

                # delete all segments belonging to this user 
                segs = [{"segment": elem, "explanation": ""} for elem in wordninja.split(undo_leetspeak(pwd))]

                for i, seg_dict in enumerate(segs):
                    seg = seg_dict['segment']
                    prompt = f'What might "{seg}" be referring to? Respond with just the answer, under 10 words.'
                    response = generate_explanation(prompt)
                    seg_dict['explanation'] = response

                    print(seg, response)

                # for i, seg in enumerate(segs):
                    seg_dict["new_segment"] = ""
                    seg_dict["num"] = str(i)
                    seg_dict["segment_name"] = f"segment_{i}"
                    seg_dict["explanation_name"] = f"explanation_{i}"
                    seg_dict["new_segment_name"] = f"new_segment_{i}"
                    seg_dict["generate"] = f"generate_{i}"
                    seg_dict["del"] = f"delete_{i}"


                    # create objects
                    seg_object = segmentObject()
                    seg_object.index = i

                    # old segment
                    seg_object.old_segment = seg_dict["segment"]
                    seg_object.old_segment_prev = []

                    # old explanation
                    seg_object.old_explanation = seg_dict["explanation"]
                    seg_object.old_explanation_outdated = False
                    seg_object.old_explanation_prev = []

                    # new segment
                    seg_object.new_segment =  ""
                    seg_object.new_segment_prev = []

                    # new explanation
                    seg_object.new_explanation =  ""
                    seg_object.new_explanation_prev = []

                    seg_object.user = user
                    seg_object.custom_user = custom_user

                    print("saved")
                    seg_object.save()

def generate_seg_exp_chain(old_seg, old_exp, bm=1, temp=1.5, ind=0, lastchain=""):
    if old_exp == None or old_exp == "": elem_str = f'"{old_seg}"'
    else: elem_str = f'"{old_seg}" ({old_exp})'

    assoc1 = old_seg
    curr_temp = temp
    attempts = 0
    while assoc1.lower() in [old_seg.lower()] and attempts < 10:
        prompt = get_prompt(elem_str, attempts)
        assoc1 = generate(prompt, max_tok=16, temp=temp, return_full_text=True).split()[0].replace(".", "")
        curr_temp = min(1.9, curr_temp + 0.05)
        attempts += 1

    assoc2 = assoc1
    curr_temp = temp
    attempts = 0
    while assoc2.lower() in [old_seg.lower(), assoc1.lower()] and attempts < 10:
        prompt = get_prompt(f'"{assoc1}"', attempts)
        assoc2 = generate(prompt, max_tok=16, temp=temp, return_full_text=True).split()[0].replace(".", "")
        curr_temp = min(1.9, curr_temp + 0.05)
        attempts += 1

    assoc3 = assoc2
    curr_temp = temp
    attempts = 0
    while assoc3.lower() in [old_seg.lower(), assoc1.lower(), assoc2.lower()] and attempts < 10:
        prompt = get_prompt(f'"{assoc2}"', attempts)
        assoc3 = generate(prompt, max_tok=16, temp=temp, return_full_text=True).split()[0].replace(".", "")
        curr_temp = min(1.9, curr_temp + 0.05)
        attempts += 1

    return assoc1, assoc2, assoc3


def get_chain(request):

    seg = request.POST["seg"]
    segexp = request.POST["segexp"]
    temp = float(request.POST["temp"])

    if temp < 0.1: temp = 0.1
    if temp > 1.9: temp = 1.9

    if "ind" in request.POST:
        ind = int(request.POST["ind"])
        lastchain = request.POST["lastchain"]
        context = {"seg": seg,
                "segexp": segexp}
        seen_vals = {seg, lastchain}
        for ind_gen in range(1, 5):
            if ind_gen > ind:
                prompt = f'What is a word related to {lastchain}? Return one word, and nothing else.'
                while lastchain in seen_vals:
                    lastchain = generate(prompt, max_tok=16, temp=temp, return_full_text=True).split()[0].replace(".", "")
            else:
                lastchain = request.POST[f"chain{ind_gen}"]
            context[f"chain{ind_gen}"] = lastchain
            seen_vals.add(lastchain)

    else:
        chain1, chain2, chain3, chain4 = generate_seg_exp_chain(seg, segexp, temp=temp)
        context = {"seg": seg,
                    "segexp": segexp,
                    "chain1": chain1,
                    "chain2": chain2,
                    "chain3": chain3,
                    "chain4": chain4,
                    }

    response_json = json.dumps(context)

    return HttpResponse(response_json, content_type='application/json')

@login_required
def increment_stage_page(request):
    custom_user = customUser.objects.get(user=request.user)  
    show_button = True
    if custom_user.stage == 1 and custom_user.substage == 3:
        info = "Thank you for completing stage 1 of the study. We may contact you for further follow ups. Please return to Prolific."
        link = f"https://app.prolific.com/submissions/complete?cc={PROLIFIC_CODE}"
    elif custom_user.stage == 2 and custom_user.substage == 4:
        info = "Thank you for completing stage 2 of the study. We may contact you for further follow ups. Please return to Prolific."
    elif custom_user.stage == 3 and custom_user.substage == 2:
        info = "Thank you for completing the final stage of this study. Please return to Prolific."
        show_button = False
    else: 
        return homepage(request)
    return render(request, 'pwd_web/increment_stage.html', {"info": info, "show_button": show_button})

@login_required
def increment_stage(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    custom_user = customUser.objects.get(user=request.user)  
    custom_user.stage += 1
    custom_user.stage = min(3, custom_user.stage)
    custom_user.substage = 0
    custom_user.last_access = datetime.now()
    custom_user.save()

    uname = request.user.username

    logout(request)
    if custom_user.stage == 1 and custom_user.substage == 3: # will not happen
        return login_with_id(request, prolific_id=uname, login_case=1)
    elif custom_user.stage == 2 and custom_user.substage == 4:
        return login_with_id(request, prolific_id=uname, login_case=2)
    else:
        return login_with_id(request, prolific_id=uname, login_case=4)

    return homepage(request)

@login_required
def demo_survey(request):
    custom_user = customUser.objects.get(user=request.user)  
    return render(request, 'pwd_web/demo_survey.html', {"username": request.user.username})

@login_required
def survey_done(request):
    if request.method != 'GET':
        return _my_json_error_response("You must use a GET request for this operation", status=405)

    custom_user = customUser.objects.get(user=request.user)  
    uname = request.user.username
    if custom_user.stage == 1: 
        custom_user.substage = 3
        custom_user.save()
        return increment_stage_page(request)
    elif custom_user.stage == 2: 
        if custom_user.substage == 0:
            custom_user.substage = 1
            custom_user.save()
            return homepage(request)
        if custom_user.substage == 2:
            custom_user.substage = 3
            custom_user.save()
            logout(request)
            return login_with_id(request, prolific_id=uname, login_case=3)
    elif custom_user.stage == 3: 
        custom_user.substage = 2
        custom_user.save()
        return homepage(request)

    custom_user.save()
    return logout_click(request)

@login_required
def pre_replacement_survey(request):
    return render(request, 'pwd_web/pre_replacement_survey.html', {"username": request.user.username})

@login_required
def post_tool_survey(request):
    return render(request, 'pwd_web/post_tool_survey.html', {"username": request.user.username})

@login_required
def post_manual_survey(request):
    custom_user = customUser.objects.get(user=request.user)  
    return render(request, 'pwd_web/post_manual_survey.html', {"username": request.user.username})

@login_required
def logout_click(request):
    logout(request)
    return login_page(request)

@login_required
def begin_replacement(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)
    custom_user = customUser.objects.get(user=request.user)  
    if custom_user.group == 0:
        return replace_manually(request)
    else:
        return view_segmentation(request)

@login_required
def replace_manually(request):
    custom_user = customUser.objects.get(user=request.user)  
    if custom_user.group != 0: return homepage(request)
    return render(request, 'pwd_web/replace_manually.html', {})

def try_register(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    uname = request.POST["username"]
    pwd = request.POST["password"]
    pwd2 = request.POST["password2"]

    if pwd != pwd2:

        log_object = log(
            type="register_mismatch",
            uname= uname,
            pwd= pwd,
            pwd2= pwd2,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        return render(request, 'pwd_web/register.html', {"error_msg": "Passwords do not match"})

    if len(User.objects.filter(username=uname)) != 0:

        log_object = log(
            type="register_bad_uname",
            uname= uname,
            pwd= pwd,
            pwd2= pwd2,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()
        return login_with_id(request, uname)

    if uname == "":
        log_object = log(
            type="register_no_uname",
            uname= uname,
            pwd= pwd,
            pwd2= pwd2,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        return render(request, 'pwd_web/register.html', {"error_msg": "Username cannot be empty"})

    if pwd == "":
        log_object = log(
            type="register_no_pwd",
            uname= uname,
            pwd= pwd,
            pwd2= pwd2,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        return render(request, 'pwd_web/register.html', {"error_msg": "Password cannot be empty"})

    if uname.count(' ') != 0 or pwd.count(' ') != 0:
        log_object = log(
            type="register_spaces",
            uname= uname,
            pwd= pwd,
            pwd2= pwd2,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        return render(request, 'pwd_web/register.html', {"error_msg": "Username or password cannot have spaces"})

    if len(pwd) < 8:
        log_object = log(
            type="register_short",
            uname= uname,
            pwd= pwd,
            pwd2= pwd2,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        return render(request, 'pwd_web/register.html', {"error_msg": "Password must be at least 8 characters."})



    user = User.objects.create_user(username=uname, password=pwd)
    user.save()

    create_new_pwd_and_segments(user, pwd)

    log_object = log(
        type="register_confirm",
        uname= uname,
        pwd= pwd,
        pwd2= pwd2,
        py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    )
    log_object.save()

    return login_with_id(request, uname)

def try_login(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    uname = request.POST["username"]
    pwd = request.POST["password"]
    if len(list(User.objects.filter(username=uname))) == 0:

        log_object = log(
            type = "login_bad_uname",
            uname= uname,
            pwd= pwd,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        return login_with_id(request, prolific_id=uname, login_case=request.POST["login_case"], error_msg="No user with this username matches")
    else:
        user = authenticate(request, username=uname, password=pwd)
        if user == None: 
            login_failures_count = AccessAttempt.objects.filter(
                    ip_address = request.META['REMOTE_ADDR']
                ).order_by("username").values("username").annotate(
                    login_failures_count = Sum("failures_since_start")
                ).values("login_failures_count")[0]['login_failures_count']

            log_object = log(
                type="login_bad_pwd",
                uname= uname,
                pwd= pwd,
                py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            log_object.save()

            error_msg = "Login failed."
            if login_failures_count >=4:
                error_msg += f" {login_failures_count} login failures, {5-login_failures_count} remaining."
            return login_with_id(request, prolific_id=uname, login_case=request.POST["login_case"], error_msg=error_msg)

        log_object = log(
            type= "login_confirm",
            uname= uname,
            pwd= pwd,
            py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        log_object.save()

        custom_user = customUser.objects.get(user=request.user)  

        last_access = custom_user.last_access.replace(tzinfo=None)
        curr_access = datetime.now().replace(tzinfo=None)
        if last_access != None and (curr_access - last_access).days >= 5:
            if custom_user.stage == 1 and (custom_user.substage == 3 or custom_user.substage == 2): 
                custom_user.stage = 2
                custom_user.substage = 0
            elif custom_user.stage == 2 and custom_user.substage == 4: 
                custom_user.stage = 3
                custom_user.substage = 0

        # here, we increment substages, as necessary
        if custom_user.stage == 1 and custom_user.substage == 1:
            custom_user.substage = 2
        elif custom_user.stage == 2 and custom_user.substage == 3:
            custom_user.substage = 4
        elif custom_user.stage == 3 and custom_user.substage == 0:
            custom_user.substage = 1


        custom_user.last_access = datetime.now()
        custom_user.save()

        return homepage(request)


model_path = "Llama-3.2-3B-Instruct"
pipeline = transformer_pipeline(
    "text-generation",
    model=model_path,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="cuda",
)
print("loaded pipeline")

big_model_path = "Llama-3.1-8B-Instruct"
big_pipeline = transformer_pipeline(
    "text-generation",
    model=big_model_path,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto",
)
print("loaded big pipeline")

def generate_seg(prompt, temp=0.6):
    prompt += "Respond with just the one word answer, and nothing else. Give me one option."
    res = generate(prompt, max_tok = 32, temp=temp, deepseek=False)
    c = 0
    while len(res.split()) != 1 and c < 5: 
        res = generate(prompt, max_tok = 32, temp=temp, deepseek=False)
        c += 1
    return res.replace('"', '').replace("'", "").replace(".","")

def generate_explanation(prompt, temp=0.4, big=False):
    return generate(prompt, max_tok=64, temp=temp, deepseek=False, big=big)
    

def generate(prompt, max_tok = 64, temp=0.7, return_full_text=True, big=False):
    messages = []
    messages.append({"role": "user", "content": prompt})
    if big:
        outputs = big_pipeline(
            messages,
            max_new_tokens=max_tok,
            do_sample=True,
            temperature=temp,
            return_full_text=return_full_text,
            top_p=0.9,
        )
    else:
        outputs = pipeline(
            messages,
            max_new_tokens=max_tok,
            do_sample=True,
            temperature=temp,
            return_full_text=return_full_text,
            top_p=0.9,
        )

    response = outputs[0]["generated_text"][-1]['content'].strip()
    return response


def generate_single(prompt):
    res = generate(prompt, max_tok = 32)
    c = 0
    if len(res.split()) != 1 and c < 10: 
        res = generate(prompt, max_tok = 32)
        c += 1
    else: return res


@login_required
@ensure_csrf_cookie
def homepage(request):
    custom_user = customUser.objects.get(user=request.user)  
    stage = custom_user.stage
    substage = custom_user.substage
    if stage == 1:
        if substage == 0: return register_page(request) # this will not happen
        elif substage == 1: return login_page(request) # this will not happen
        elif substage == 2: return demo_survey(request)
        else: return increment_stage_page(request)

    elif stage == 2:
        if substage == 0: return pre_replacement_survey(request)
        elif substage == 1: return render(request, 'pwd_web/homepage.html')
        elif substage == 2: 
            if custom_user.group == 0: return post_manual_survey(request)
            else: return post_tool_survey(request)
        elif substage == 3: return logout_click(request)
        else: 
            if custom_user.group == 0:
                return redirect(f'https://app.prolific.com/submissions/complete?cc={PROLIFIC_CODE}')
            else:
                return redirect(f'https://app.prolific.com/submissions/complete?cc={PROLIFIC_CODE}')

    else:
        if substage == 2: return increment_stage_page(request)
        else: return render(request, 'pwd_web/all_done.html', {"uname": request.user.username, "old_pwd": custom_user.old_pwd, "new_pwd": custom_user.new_pwd})

@login_required
@ensure_csrf_cookie
def view_segmentation(request):
    colors = ["#012169", "#C84E00", "#00539B", "#FFD960", "#E89923", "#993399"]

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments = []
    for i, seg in enumerate(segments_query):
        seg = {"segment": seg.old_segment, "explanation": seg.old_explanation, "index": i, "color": colors[i%len(colors)]}
        segments.append(seg)

    curr_pwd = custom_user.old_pwd
    context = {"pwd": curr_pwd}
    context["segments"] = segments

    return render(request, 'pwd_web/view_segmentation.html', context)

def generate_link(item1, item2):
    if item1 == "" or item1 is None or item2 == "" or item2 is None: 
        return "Once both elements are filled, this will contain an explanation of their relationship."

    prompt = f"What is a simple but truthful and fact-based connection between {item1} and {item2}? Respond with at most 15 words."

    val = generate(prompt, temp=0.01, big=True)

    return val


@login_required
def ajax_update_exps(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    # first - delete all existing segments
    # next - create segments again
    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))

    to_update = []

    v_str = "Once both elements are filled, this will contain an explanation of their relationship."

    for seg in segments_query:

        if seg.chain1_exp == v_str or seg.chain1_exp == "loading...":
            if seg.chain1 != "" and seg.chain1 != None:
                chain1_exp = generate_link(seg.old_segment, seg.chain1)
                seg.chain1_exp = chain1_exp

                to_update.append({
                    "seg_ind": seg.index,
                    "chain_ind": 1,
                    "val": chain1_exp,
                    "val_type": get_chaintype(chain1_exp),
                })
        
        if seg.chain2_exp == v_str or seg.chain2_exp == "loading...":
            if seg.chain1 != "" and seg.chain1 != None:
                if seg.chain2 != "" and seg.chain2 != None:
                    chain2_exp = generate_link(seg.chain1, seg.chain2)
                    seg.chain2_exp = chain2_exp

                    to_update.append({
                        "seg_ind": seg.index,
                        "chain_ind": 2,
                        "val": chain2_exp,
                        "val_type": get_chaintype(chain2_exp),
                    })
        
        if seg.chain3_exp == v_str or seg.chain3_exp == "loading...":
            if seg.chain3 != "" and seg.chain3 != None:
                if seg.chain2 != "" and seg.chain2 != None:
                    chain3_exp = generate_link(seg.chain2, seg.chain3)
                    seg.chain3_exp = chain3_exp

                    to_update.append({
                        "seg_ind": seg.index,
                        "chain_ind": 3,
                        "val": chain3_exp,
                        "val_type": get_chaintype(chain3_exp),
                    })

        seg.save()

    
    response_json = json.dumps(to_update)

    return HttpResponse(response_json, content_type='application/json')

@login_required
def ajax_reset_segments_chain(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    # first - delete all existing segments
    # next - create segments again
    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))

    for seg in segments_query:
        seg.delete()

    for i in range(len(custom_user.old_segments_for_reset)):
        seg = segmentObject()
        seg.index = i
        seg.old_segment = custom_user.original_old_segments[i]
        seg.old_explanation = custom_user.original_old_explanations[i]
        seg.chain1 = custom_user.old_chain1_for_reset[i]
        seg.chain2 = custom_user.old_chain2_for_reset[i]
        seg.chain3 = custom_user.old_chain3_for_reset[i]
        seg.prev_chain1 = ""
        seg.prev_chain2 = ""
        seg.prev_chain3 = ""
        seg.user = request.user
        seg.custom_user = custom_user
        seg.save()
        
    _, _ = get_new_pwds_chain(custom_user)

    return get_segments_chain(request)

@login_required
def ajax_regen_segment_chain(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    seg_ind = int(request.POST['seg_ind'])

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)

    seg = segments_query[seg_ind]

    chain1, chain2, chain3 = generate_seg_exp_chain(seg.old_segment, seg.old_explanation)
    seg.prev_chain1 = seg.chain1
    seg.prev_chain2 = seg.chain2
    seg.prev_chain3 = seg.chain3
    seg.prev_chain1_exp = seg.chain1_exp
    seg.prev_chain2_exp = seg.chain2_exp
    seg.prev_chain3_exp = seg.chain3_exp
    seg.chain1 = chain1
    seg.chain1_exp = "loading..."
    seg.chain2 = chain2
    seg.chain2_exp = "loading..."
    seg.chain3 = chain3
    seg.chain3_exp = "loading..."
    seg.save()
    _, _ = get_new_pwds_chain(custom_user)

    return get_segments_chain(request)


def get_prompt(elem, attempt):
    basic_prompt = f'For a user that has {elem} in their password, what is a closely related string that they can use instead?'
    other_prompts = [
        f'For a user that has {elem} in their password, what is a similar word that they can use instead?',
        f'What is a word or string related to {elem}?',
        f'What is the first word that you think of when you hear {elem}?'
    ]

    if attempt < 2: prompt = basic_prompt
    else:
        prompt = random.choice([basic_prompt] + other_prompts)

    prompt += ' Return one word, and nothing else.'

    return prompt

@login_required
def ajax_edit_segment_chain(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    seg_ind = int(request.POST['seg_ind'])
    chain_ind = int(request.POST['chain_ind'])
    val = request.POST['val']

    if chain_ind == 0:
        return ajax_regen_segment_chain(request)

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)

    seg = segments_query[seg_ind]

    seg.prev_chain1 = seg.chain1
    seg.prev_chain2 = seg.chain2
    seg.prev_chain3 = seg.chain3
    seg.prev_chain1_exp = seg.chain1_exp
    seg.prev_chain2_exp = seg.chain2_exp
    seg.prev_chain3_exp = seg.chain3_exp

    if chain_ind == 3:
        seg.chain3 = val
        seg.chain3_exp = "loading..."
    else:
        if chain_ind == 1:
            if val != seg.chain1: seg.chain1_exp = "loading..."
            seg.chain1 = val
            seg.chain2_exp = "loading..."
            seen_elem = {seg.old_segment.lower(), val.lower()}
            chain2 = val
            curr_temp = 1.5
            attempts = 0
            while chain2.lower() in seen_elem and attempts < 10:
                prompt = get_prompt(f'"{val}"', attempts)
                chain2 = generate(prompt, max_tok=16, temp=curr_temp, return_full_text=True).split()[0].replace(".", "")
                curr_temp = min(1.9, curr_temp + 0.05)
                attempts += 1

            seen_elem.add(chain2.lower())
            seg.prev_chain2 = seg.chain2
            seg.chain2 = chain2
        if chain_ind == 2:
            chain2 = val
            if val != seg.chain2: seg.chain2_exp = "loading..."
            seg.chain2 = val
            seen_elem = {seg.old_segment.lower(), seg.chain1.lower(), val.lower()}
            
        chain3 = val
        seg.chain3_exp = "loading..."
        curr_temp = 1.5
        attempts = 0
        while chain3.lower() in seen_elem and attempts < 10:
            prompt = get_prompt(f'"{chain2}"', attempts)
            chain3 = generate(prompt, max_tok=16, temp=curr_temp, return_full_text=True).split()[0].replace(".", "")
            curr_temp = min(1.9, curr_temp + 0.05)
            attempts += 1
        seg.chain3 = chain3

    seg.save()
    _, _ = get_new_pwds_chain(custom_user)
    
    return get_segments_chain(request)


@login_required
def ajax_try_exp_regen(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    i = int(request.POST['item_id'])

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)

    seg = segments_query[i]

    prompt = f'What might "{seg.old_segment}" be referring to? Respond with just the answer, under 10 words.'
    response = generate_explanation(prompt, temp=0.8)
    seg.old_explanation = response
    seg.old_explanation_auto = True
    seg.count_exp_replacements += 1
    add_note = False
    if seg.count_exp_replacements % 3 == 0:
        add_note = True

    seg.save()
    
    return get_segments_chain(request, add_note=add_note)

@login_required
def ajax_delete_segment(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    item_id = int(request.POST['item_id'])

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)

    deleted_prev = False


    for i, seg in enumerate(segments_query):
        if i == item_id and len(segments_query) != 1:
            custom_user.old_segment = seg.old_segment
            custom_user.old_segment_prev = seg.old_segment_prev
            custom_user.old_explanation = seg.old_explanation
            custom_user.old_explanation_prev = seg.old_explanation_prev
            custom_user.new_segment = seg.new_segment
            custom_user.new_segment_prev = seg.new_segment_prev
            custom_user.new_explanation = seg.new_explanation
            custom_user.new_explanation_prev = seg.new_explanation_prev

            seg.delete()
            deleted_prev = True
        elif deleted_prev:
            seg.index -= 1
            seg.save()

    _, _ = get_new_pwds(custom_user)

    return get_segments(request)



@login_required
def ajax_undo_segment_chain(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    item_id = int(request.POST['item_id'])

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)
    seg = segments_query[item_id]
    seg.undo_segment_chain()
    seg.save()
    _, _ = get_new_pwds_chain(custom_user)

    return get_segments_chain(request)

@login_required
def ajax_get_more_passwords(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    pwd_ind = int(request.POST['pwd_ind'])

    custom_user = customUser.objects.get(user=request.user)
    _, _ = get_new_pwds_chain(custom_user, generate_more=True)


    return get_segments_chain(request, pwd_ind)

@login_required
def ajax_new_segment(request):
    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)

    seg = segmentObject()
    seg.index = len(segments_query)
    seg.old_segment = ""
    seg.old_segment_prev = []
    seg.old_explanation = ""
    seg.old_explanation_outdated = True
    seg.old_explanation_prev = []
    seg.new_segment = ""
    seg.new_segment_prev = []
    seg.new_explanation =  ""
    seg.new_explanation_prev = []
    seg.user = request.user
    seg.custom_user = custom_user


    seg.save()
    return get_segments(request)

def get_segments(request, pwds_ind = 0):
    custom_user = customUser.objects.get(user=request.user)
    if custom_user.new_pwd != "":
        return render(request, 'pwd_web/all_done.html', {"uname": request.user.username, "old_pwd": custom_user.old_pwd, "new_pwd": custom_user.new_pwd})

    colors = ["#012169", "#C84E00", "#00539B", "#FFD960", "#E89923", "#993399"]

    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)
    all_old_segs = [x.old_segment for x in segments_query]

    segments = []

    if custom_user.perm_suggestions == None: perm_suggestions = []
    else:
        perm_suggestions = custom_user.perm_suggestions
    if custom_user.gen_suggestions == None: gen_suggestions = []
    else: gen_suggestions = custom_user.gen_suggestions
    new_pwds = list(filter(lambda x: len(x) >= 8, perm_suggestions + gen_suggestions))

    all_new_segs = []

    many_tries = False
    for i, seg in enumerate(segments_query):
        if seg.new_segment != "": all_new_segs.append(seg.new_segment)
        if seg.count_replacements == 5: many_tries = True
        seg = {
            "old_segment": seg.old_segment, 
            "old_explanation": seg.old_explanation, 
            "old_explanation_outdated": seg.old_explanation_outdated, 
            "new_segment": seg.new_segment, 
            "new_explanation": seg.new_explanation, 
            "id": i, 
            "color": colors[i%len(colors)]}
        segments.append(seg)

    if len(all_new_segs) != 0:
        pass

    response_dict = {"pwds_ind": pwds_ind, 
        "all_segments": segments, 
        "new_pwds": new_pwds
        }

    if custom_user.new_segment != "" and custom_user.new_segment != None:
        response_dict["undo_possible"] = "true"

    if len(new_pwds) == 0 and any([x.new_segment in all_old_segs for x in segments_query]):
        response_dict["error_msg"] = "Note: At least one element must differ from the elements of the original password."
    elif many_tries: 
        response_dict["error_msg"] = "Note: If you are unsatisfied with the generated replacements, feel free to select one manually."

    

    response_json = json.dumps(response_dict)

    return HttpResponse(response_json, content_type='application/json')


def login_log_change(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    uname = request.POST['uname']
    pwd = request.POST['pwd']
    timestr = request.POST['time']

    log_object = log(
        type="login_change",
        uname= uname,
        pwd= pwd,
        py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        js_time= timestr
    )
    log_object.save()

    return HttpResponse(all_logs, content_type='application/json')


def register_log_change(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    uname = request.POST['uname']
    pwd1 = request.POST['pwd1']
    pwd2 = request.POST['pwd2']
    timestr = request.POST['time']

    log_object = log(
        type="register_change",
        uname= uname,
        pwd= pwd1,
        pwd2= pwd2,
        py_time= datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        js_time= timestr
    )
    log_object.save()


    return HttpResponse(all_logs, content_type='application/json')

@login_required
def confirm_segmentation(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    custom_user = customUser.objects.get(user=request.user)
    if custom_user.new_pwd != "":
        return render(request, 'pwd_web/all_done.html', {"uname": request.user.username, "old_pwd": custom_user.old_pwd, "new_pwd": custom_user.new_pwd})

    custom_user = customUser.objects.get(user=request.user)
    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)

    original_old_segments = []
    original_old_explanations = []
    old_chain1_for_reset = []
    old_chain2_for_reset = []
    old_chain3_for_reset = []


    for seg in segments_query:
        original_old_segments.append(seg.old_segment)
        original_old_explanations.append(seg.old_explanation)

        old_chain1_for_reset.append(seg.chain1)
        old_chain2_for_reset.append(seg.chain2)
        old_chain3_for_reset.append(seg.chain3)

    custom_user.old_segments_for_reset = original_old_segments
    custom_user.old_explanations_for_reset = original_old_explanations

    custom_user.old_chain1_for_reset = old_chain1_for_reset
    custom_user.old_chain2_for_reset = old_chain2_for_reset
    custom_user.old_chain3_for_reset = old_chain3_for_reset


    custom_user.save()

    _, _ = get_new_pwds_chain(custom_user)

    return new_segments2(request)

def get_chaintype(v):
    if v == "Once both elements are filled, this will contain an explanation of their relationship.":
        return "disabled_tooltip"
    if v == "loading...":
        return "disabled_tooltip"
    return "tooltip"

def get_segments_chain(request, pwds_ind = 0, add_note = False):
    custom_user = customUser.objects.get(user=request.user)
    if custom_user.new_pwd != "":
        return render(request, 'pwd_web/all_done.html', {"uname": request.user.username, "old_pwd": custom_user.old_pwd, "new_pwd": custom_user.new_pwd})

    colors = ["#012169", "#C84E00", "#00539B", "#FFD960", "#E89923", "#993399"]

    segments_query = list(segmentObject.objects.filter(custom_user=custom_user))
    
    segments_query.sort(key=lambda seg: seg.index)
    all_old_segs = [x.old_segment for x in segments_query]

    segments = []

    if custom_user.perm_suggestions == None: perm_suggestions = []
    else:
        perm_suggestions = custom_user.perm_suggestions
    if custom_user.gen_suggestions == None: gen_suggestions = []
    else: gen_suggestions = custom_user.gen_suggestions
    new_pwds = list(filter(lambda x: len(x) >= 8, perm_suggestions + gen_suggestions))

    all_new_segs = []

    many_tries = False
    for i, seg in enumerate(segments_query):
        seg = {
            "old_segment": seg.old_segment, 
            "old_explanation": seg.old_explanation, 
            "old_explanation_outdated": seg.old_explanation_outdated, 
            "chain1": seg.chain1,
            "chain2": seg.chain2,
            "chain3": seg.chain3,
            "chain1_exp": seg.chain1_exp,
            "chain2_exp": seg.chain2_exp,
            "chain3_exp": seg.chain3_exp,
            "chain1_exp_type": get_chaintype(seg.chain1_exp),
            "chain2_exp_type": get_chaintype(seg.chain2_exp),
            "chain3_exp_type": get_chaintype(seg.chain3_exp),
            "can_undo": seg.can_undo_chain(),
            "id": i, 
            "color": colors[i%len(colors)]}
        segments.append(seg)

    if len(all_new_segs) != 0:
        pass

    response_dict = {
        "all_segments": segments, 
        "pwds_ind": pwds_ind, 
        "new_pwds": new_pwds
        }
    if add_note:
        response_dict["segment_note"] = "Note: If you are unsatisfied with the generated explanation, feel free to write one manually."

    response_json = json.dumps(response_dict)

    return HttpResponse(response_json, content_type='application/json')

def new_segments2(request):
    custom_user = customUser.objects.get(user=request.user)
    pwd = custom_user.old_pwd

    context = {"seg": "Anna",
                "segexp": "my name",
                "chain1": "chain1_ex",
                "chain2": "chain2_ex",
                "chain3": "chain3_ex",
                "chain4": "chain4_ex",
                "pwd": pwd
                }

    for elem in request.POST:
        if "set_pwd_to__" in elem:
            new_pwd = elem.split("__")[1]
            custom_user.new_pwd_selected = new_pwd
            custom_user.save()
            context['new_pwd'] = new_pwd

            return render(request, 'pwd_web/confirm_pwd.html', context)

    return render(request, 'pwd_web/new_segments2.html', context)

def perm_pwd(arr):
    if sum([len(v) for v in arr]) < 18: return ["".join(item).replace(" ", "") for item in set(list(itertools.permutations(arr)))]

    retvals = []
    while len(retvals) < 2:
        random.shuffle(arr)
        retval = ""
        i = 0
        while len(retval) < 18 and i < len(arr):
            retval += arr[i]
            i += 1
        retvals.append(retval)

    return retvals

def programatic_pwd(arr):
    new_pwd = "hi"

    new_arr = []

    random.shuffle(arr)
    totlen = 0

    # capitalization options - all caps, only first char, all lower (random for each word)
    for elem in arr:
        if totlen < 18:
            elem = elem.chain3.strip()
            cap_method = random.choice(["all", "none", "none", "none", "first"])
            if cap_method == "all": elem = elem.upper()
            elif cap_method == "none": elem = elem.lower()
            else: elem = elem[:1].upper() + elem[1:].lower()

            # character replacement options
                # e or E -> 3
                # a -> @
                # A -> 4
                # I or l -> 1
                # o or O -> 0
            new_elem = ""
            for c in elem:
                if c == "E":
                    if random.randint(0, 10) < 1: new_elem += "3"
                    else: new_elem += c
                elif c == "a":
                    if random.randint(0, 10) < 1: new_elem += "@"
                    else: new_elem += c
                elif c == "A":
                    if random.randint(0, 10) < 1: new_elem += "4"
                    else: new_elem += c
                elif c == "I" or c == "l":
                    if random.randint(0, 10) < 1: new_elem += "1"
                    else: new_elem += c
                elif c == "o" or c == "O":
                    if random.randint(0, 10) < 1: new_elem += "0"
                    else: new_elem += c
                else: new_elem += c
            
            new_arr.append(new_elem)
            totlen += len(new_elem)


    # have 0-2 random chars in a row
    special_chars = ["!", "@", "#", "$", "%", "&"]
    # l = random.randint(0,2)
    l = random.choice([0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 3])
    if l != 0: new_arr.append("".join([str(random.choice(special_chars)) for _ in range(l)]))

    # have 0-2 random nums in a row
    # l = random.randint(0,2)
    l = random.choice([0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 2, 3])
    if l != 0: new_arr.append("".join([str(random.randint(0, 9)) for _ in range(l)]))

    random.shuffle(new_arr)

    # combine new elements in random order
    # maybe combine them with "_", maybe with nothing
    if random.randint(0, 10) < 2: return "_".join(new_arr)
    elif random.randint(0, 10) < 2: return ".".join(new_arr)
    else: return "".join(new_arr)

    # return new_pwd

def get_new_pwds_chain(custom_user, generate_more=False, gen_count=18):
    all_segs = list(segmentObject.objects.filter(custom_user=custom_user))
    all_segs.sort(key=lambda seg: seg.index)
    all_old_segs = [x.old_segment for x in all_segs]
    if any([x.chain3 == "" for x in all_segs]): return [], []
    all_segs = list(filter(lambda x: x.chain3 != "" and x.chain3 != None and x.chain3 not in all_old_segs, all_segs))

    pwd = custom_user.old_pwd

    if len(all_segs) != 0:
        if generate_more:
            new_pwds_perm = []
            
        else:
            custom_user.gen_suggestions = None
            new_segs = []
            for seg in all_segs:
                new_segs.append(seg.chain3)
            
            correct_order_pwd = "".join(new_segs)
            new_pwds_perm = perm_pwd(new_segs)
            if correct_order_pwd in new_pwds_perm: new_pwds_perm.remove(correct_order_pwd)
            random.shuffle(new_pwds_perm)
            new_pwds_perm = [correct_order_pwd] + new_pwds_perm

            new_pwds_perm = [new_pwd_perm for new_pwd_perm in new_pwds_perm if len(new_pwd_perm) >= 8]

            if len(new_pwds_perm) > gen_count:
                new_pwds_perm = new_pwds_perm[:gen_count]

            custom_user.perm_suggestions = new_pwds_perm


        new_pwds_gen = []

        while len(new_pwds_gen) < (gen_count - len(new_pwds_perm)):
            curr_gen = programatic_pwd(all_segs)
            if curr_gen not in new_pwds_gen and len(curr_gen) >= 8: new_pwds_gen.append(curr_gen)

    else:
        new_pwds_perm = []
        new_pwds_gen = []

    if custom_user.gen_suggestions == None: custom_user.gen_suggestions = new_pwds_gen
    else: custom_user.gen_suggestions += new_pwds_gen
    custom_user.save()

    return new_pwds_perm, new_pwds_gen

def get_new_pwds(custom_user, generate_more=False, gen_count=18):
    all_segs = list(segmentObject.objects.filter(custom_user=custom_user))
    all_segs.sort(key=lambda seg: seg.index)
    all_old_segs = [x.old_segment for x in all_segs]
    all_segs = list(filter(lambda x: x.new_segment != "" and x.new_segment != None and x.new_segment not in all_old_segs, all_segs))

    pwd = custom_user.old_pwd

    if len(all_segs) != 0:
        if generate_more:
            new_pwds_perm = []
            
        else:
            custom_user.gen_suggestions = None
            new_segs = []
            for seg in all_segs:
                new_segs.append(seg.new_segment)
            
            correct_order_pwd = "".join(new_segs)
            new_pwds_perm = perm_pwd(new_segs)
            if correct_order_pwd in new_pwds_perm: new_pwds_perm.remove(correct_order_pwd)
            random.shuffle(new_pwds_perm)
            new_pwds_perm = [correct_order_pwd] + new_pwds_perm

            new_pwds_perm = [new_pwd_perm for new_pwd_perm in new_pwds_perm if len(new_pwd_perm) >= 8]

            if len(new_pwds_perm) > gen_count:
                new_pwds_perm = new_pwds_perm[:gen_count]

            custom_user.perm_suggestions = new_pwds_perm


        new_pwds_gen = []

        while len(new_pwds_gen) < (gen_count - len(new_pwds_perm)):
            curr_gen = programatic_pwd(all_segs)
            if curr_gen not in new_pwds_gen and len(curr_gen) >= 8: new_pwds_gen.append(curr_gen)

    else:
        new_pwds_perm = []
        new_pwds_gen = []

    if custom_user.gen_suggestions == None: custom_user.gen_suggestions = new_pwds_gen
    else: custom_user.gen_suggestions += new_pwds_gen
    custom_user.save()

    return new_pwds_perm, new_pwds_gen


@login_required
def set_new(request):

    if request.method != 'POST':
        return _my_json_error_response("You must use a POST request for this operation", status=405)

    custom_user = customUser.objects.get(user=request.user)  
    uname = request.user.username
    group = custom_user.group

    if 'new_pwd_ref' in request.POST: new_pwd_ref = request.POST['new_pwd_ref']
    new_pwd = request.POST['new_pwd']
    old_pwd = custom_user.old_pwd

    redir_url = "replace_manually" if custom_user.group == 0 else "confirm_pwd"

    placeholder_pwd = new_pwd if custom_user.group == 0 else new_pwd_ref

    if old_pwd == new_pwd:
        return render(request, f'pwd_web/{redir_url}.html', {"new_pwd": placeholder_pwd, "error_msg": "New password cannot be the same as original password."})
    
    if new_pwd == "":
        return render(request, f'pwd_web/{redir_url}.html', {"new_pwd": placeholder_pwd, "error_msg": "New password cannot be empty."})
    
    if len(new_pwd) < 8:
        return render(request, f'pwd_web/{redir_url}.html', {"new_pwd": placeholder_pwd, "error_msg": "New password must be at least 8 characters."})
    
    if new_pwd.count(' ') != 0:
        return render(request, f'pwd_web/{redir_url}.html', {"new_pwd": placeholder_pwd, "error_msg": "New password cannot have spaces."})
    

    custom_user.new_pwd = new_pwd
    custom_user.substage = 2
    custom_user.save()
    
    request.user.set_password(new_pwd)
    request.user.save()

    user = authenticate(request, username=uname, password=new_pwd)
    login(request, user)

    all_results = json.load(open("staticfiles/results.json", "r"))
    all_results[uname] = {
        "old_pwd": old_pwd,
        "new_pwd": new_pwd,
        "group": 0
    }

    if group == 0:
        return post_manual_survey(request)
    else:
        all_segs = list(segmentObject.objects.filter(custom_user=custom_user))
        all_results[uname]['group'] = 1
        all_results[uname]['segments'] = {seg.old_segment: seg.old_explanation for seg in all_segs}
        all_results[uname]['new_segments'] = {seg.old_segment: {seg.new_segment: seg.new_explanation} for seg in all_segs}
        all_results[uname]['suggested_pwds_perm'] = custom_user.perm_suggestions
        all_results[uname]['suggested_pwds_gen'] = custom_user.gen_suggestions
        return post_tool_survey(request)

def confirm_pwd(request):
    
    return render(request, 'pwd_web/confirm_pwd.html')
