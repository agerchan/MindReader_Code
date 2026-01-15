"""webapps URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from pwd_web import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path('get_chain', views.get_chain, name='get_chain'), 
    path('', views.homepage, name='homepage'),
    path('login', views.login_page, name='login'),
    path('login/<str:prolific_id>', views.login_with_id, name='login_with_id'),
    path('intro', views.intro, name='intro'),
    path('stage_intro', views.stage_intro, name='stage_intro'),
    path('intro2', views.intro2, name='intro2'),
    path('intro3', views.intro3, name='intro3'),
    path('consent', views.consent, name='consent'),
    path('intro/<str:prolific_id>', views.intro_with_id, name='intro_with_id'),
    path('stage_intro/<str:prolific_id>', views.stage_intro_with_id, name='stage_intro_with_id'),
    path('intro2/<str:prolific_id>/<str:group>/', views.intro2_with_id, name='intro2_with_id'),
    path('intro3/<str:prolific_id>', views.intro3_with_id, name='intro3_with_id'),
    path('logout', views.logout_click, name='logout'),
    path('begin_replacement', views.begin_replacement, name='begin_replacement'),
    path('replace_manually', views.replace_manually, name='replace_manually'),
    path('demo_survey', views.demo_survey, name='demo_survey'),
    path('survey_done', views.survey_done, name='survey_done'),
    path('pre_replacement_survey', views.pre_replacement_survey, name='pre_replacement_survey'),
    path('post_tool_survey', views.post_tool_survey, name='post_tool_survey'),
    path('increment_stage_page', views.increment_stage_page, name='increment_stage_page'),
    path('increment_stage', views.increment_stage, name='increment_stage'),
    path('post_manual_survey', views.post_manual_survey, name='post_manual_survey'),
    path('login_log_change', views.login_log_change, name='login_log_change'),
    path('register_log_change', views.register_log_change, name='register_log_change'),
    path('register', views.register_page, name='register'),
    path('register/<str:prolific_id>', views.register_with_id, name='register_with_id'),
    path('try_register', views.try_register, name='try_register'),
    path('try_login', views.try_login, name='try_login'),
    path('set_new', views.set_new, name='set_new'),
    path('confirm_pwd', views.confirm_pwd, name='confirm_pwd'), 
    path('get_segments', views.get_segments, name='get_segments'), 
    path('get_segments_chain', views.get_segments_chain, name='get_segments_chain'), 
    path('homepage', views.homepage, name='homepage'), 
    path('new_segment', views.ajax_new_segment, name='new_segment'), 
    path('delete_segment', views.ajax_delete_segment, name='delete_segment'),
    path('undo_segment_chain', views.ajax_undo_segment_chain, name='undo_segment_chain'),
    path('undo_delete', views.ajax_undo_delete, name='undo_delete'),
    path('reset_segments_chain', views.ajax_reset_segments_chain, name='reset_segments_chain'),
    path('get_more_passwords', views.ajax_get_more_passwords, name='get_more_passwords'),
    path('update_exps', views.ajax_update_exps, name="update_exps"),
    path('edit_segment_chain', views.ajax_edit_segment_chain, name='edit_segment_chain'),
    path('regen_segment_chain', views.ajax_regen_segment_chain, name='regen_segment_chain'),
    path('new_segments2', views.new_segments2, name='new_segments2'),
    path('try_exp_regen', views.ajax_try_exp_regen, name='try_exp_regen'),
    path('view_segmentation', views.view_segmentation, name='view_segmentation'),
    path('confirm_segmentation', views.confirm_segmentation, name='confirm_segmentation'), 
    path('<str:someval>', views.custom404, name='custom404'),
]