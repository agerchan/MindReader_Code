from django.db import models
from separatedvaluesfield.models import SeparatedValuesField
from django.contrib.auth.models import User
from datetime import datetime

class customUser(models.Model):
  user                = models.OneToOneField(User, on_delete=models.CASCADE)
  uname               = models.CharField(max_length=100, default="")

  group             = models.IntegerField(default=1)
  stage             = models.IntegerField(default=1)
  substage          = models.IntegerField(default=0)
  
  # 1.0 before registering
  # --> register for account
  # 1.1 registered, needs to log in
  ## --> log in for the first time
  # 1.2 registered and logged in, needs to do survey
  # --> do survey (click done, in our case)
  # 1.3 all done with stage 1
  # --> 1 week / click increment stage

  # 2.0 before survey 1, after logging in
  # --> do survey 1
  # 2.1 after survey 1, needs to change pwd
  # --> change pwd
  # 2.2 after changing pwd, needs to do survey
  # --> do survey (click done)
  # 2.3 done with changing pwd and survey, needs to log back in
  ## --> log in with new pwd
  # 2.4 all done with stage 2
  # --> 1 week / click increment stage

  # 3.0 before loggging in with new pwd
  # --> log in with new pwd
  # 3.1 logged in with new pwd, needs to do survey
  # --> do survey
  # 3.2 logged in and did survey, needs to come back next week
  # --> 1 week / click increment stage
  # 3.2 go back to 3.0


  old_pwd           = models.CharField(max_length=100, default="")
  # this is what was clicked on
  new_pwd_selected  = models.CharField(max_length=100, default="")
  # this is what was entered and actually used!
  new_pwd           = models.CharField(max_length=100, default="")

  perm_suggestions  = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  gen_suggestions   = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  # originals are used in the case of reset
  # therefore, all items are lists
  original_old_segments       = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  original_old_explanations   = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  original_old_explanations_auto   = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  original_new_segments       = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  original_new_explanations   = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  original_new_segments_auto  = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  # this is if a segment is deleted
  # if undo delete is pressed!
  # the fields are the same as would be for any segment!
  old_segment           = models.CharField(max_length=100, default="")
  old_segment_prev      = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  
  old_explanation       = models.CharField(max_length=100, default="")
  old_explanation_auto  = models.BooleanField(default=True)
  old_explanation_prev  = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_explanation_prev_auto   = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  new_segment           = models.CharField(max_length=100, default="")
  new_segment_auto      = models.BooleanField(default=True)
  new_segment_prev      = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  new_segment_prev_auto = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  
  new_explanation       = models.CharField(max_length=100, default="")
  new_explanation_prev  = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  old_segments_for_reset      = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_explanations_for_reset  = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_chain1_for_reset        = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_chain2_for_reset        = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_chain3_for_reset        = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  last_access           = models.DateTimeField(null=True)

class segmentObject(models.Model):

  index                 = models.IntegerField() 

  old_segment           = models.CharField(max_length=100, default="")
  old_segment_prev      = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_explanation_outdated      = models.BooleanField(default=True)
  
  old_explanation       = models.CharField(max_length=100, default="")
  old_explanation_auto  = models.BooleanField(default=True)
  old_explanation_prev  = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  old_explanation_prev_auto   = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  chain1           = models.CharField(max_length=100, default="")
  chain2           = models.CharField(max_length=100, default="")
  chain3           = models.CharField(max_length=100, default="")
  chain1_exp           = models.CharField(max_length=100, default="Once both elements are filled, this will contain an explanation of their relationship.")
  chain2_exp           = models.CharField(max_length=100, default="Once both elements are filled, this will contain an explanation of their relationship.")
  chain3_exp           = models.CharField(max_length=100, default="Once both elements are filled, this will contain an explanation of their relationship.")

  prev_chain1           = models.CharField(max_length=100, default="")
  prev_chain2           = models.CharField(max_length=100, default="")
  prev_chain3           = models.CharField(max_length=100, default="")
  prev_chain1_exp           = models.CharField(max_length=100, default="Once both elements are filled, this will contain an explanation of their relationship.")
  prev_chain2_exp           = models.CharField(max_length=100, default="Once both elements are filled, this will contain an explanation of their relationship.")
  prev_chain3_exp           = models.CharField(max_length=100, default="Once both elements are filled, this will contain an explanation of their relationship.")

  # only keep track of if new seg is automatic
  new_segment           = models.CharField(max_length=100, default="")
  new_segment_auto      = models.BooleanField(default=True)
  new_segment_prev      = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  new_segment_prev_auto = SeparatedValuesField(max_length=100, token="\x0c", null=True)
  count_exp_replacements    = models.IntegerField(default=0)
  
  new_explanation       = models.CharField(max_length=100, default="")
  new_explanation_prev  = SeparatedValuesField(max_length=100, token="\x0c", null=True)

  count_replacements    = models.IntegerField(default=0)

  user = models.ForeignKey(User, default=None, on_delete=models.PROTECT)
  custom_user = models.ForeignKey(customUser, default=None, on_delete=models.PROTECT, null=True)

  def __str__(self):
    return f"{self.index}-{self.old_segment}"

  def update_segment(self, new_segment, is_auto=True):
    if self.new_segment_prev == None: # does not exist yet
      self.new_segment_prev = [self.new_segment]
      self.new_semgent_prev_auto = [self.new_segment_auto]
    else: # exists
      if len(self.new_segment_prev) == 0 or self.new_segment_prev[-1] != new_segment:
        self.new_segment_prev.append(self.new_segment)
        self.new_segment_prev_auto.append(self.new_segment_auto)
    self.new_segment = new_segment
    self.new_segment_auto = is_auto
    self.count_replacements += 1

  def undo_segment_chain(self):
    if self.can_undo_chain():
      self.chain1 = self.prev_chain1
      self.chain2 = self.prev_chain2
      self.chain3 = self.prev_chain3
      self.chain1_exp = self.prev_chain1_exp
      self.chain2_exp = self.prev_chain2_exp
      self.chain3_exp = self.prev_chain3_exp
      self.prev_chain1 = ""
      self.prev_chain2 = ""
      self.prev_chain3 = ""
      self.prev_chain1_exp = "Once both elements are filled, this will contain an explanation of their relationship."
      self.prev_chain2_exp = "Once both elements are filled, this will contain an explanation of their relationship."
      self.prev_chain3_exp = "Once both elements are filled, this will contain an explanation of their relationship."

  def can_undo_chain(self):
    if self.prev_chain1 != "" and self.prev_chain2 != "" and self.prev_chain3 != "":
      return True
    else: return False

  def undo_segment(self):
    if self.new_segment_prev != None and len(self.new_segment_prev) != 0:
      self.new_segment = self.new_segment_prev[-1]
      self.new_segment_auto = self.new_segment_prev_auto[-1]
      self.new_segment_prev = self.new_segment_prev[:-1]
      self.new_segment_prev_auto = self.new_segment_prev_auto[:-1]

  def update_explanation(self, new_explanation):
    if self.new_explanation_prev == None:
      self.new_explanation_prev = [self.new_explanation]
    else:
      if len(self.new_explanation_prev) == 0 or self.new_explanation_prev[-1] != new_explanation:
        self.new_explanation_prev += [self.new_explanation]
    self.new_explanation = new_explanation

  # def undo_explanation(self):
  #   if self.new_explanation_prev != None and len(self.new_explanation_prev) != 0:
  #     self.new_explanation = self.new_explanation_prev[-1]
  #     # del self.new_explanation_prev[-1]
  #     self.new_explanation_prev = self.new_explanation_prev[:-1]
  #   # print(self.new_explanation_prev, self.new_explanation)

  # def generate_from_seg(self):
  #   # here are the cases

  #   # blank before
  #   if (self.old_segment == None or self.old_segment ==  "") and (self.old_explanation == None or self.old_explanation ==  ""):
  #     r = RandomWords()
  #     rand_seed = r.get_random_word()

  #     prompt = f"What is a word or number you could use in a password, related to {rand_seed}? Respond with only that string."
  #     new_elem = generate_single(prompt)
  #     self.update_segment(new_elem)
  #     self.update_explanation("randomly selected")
  #     self.save()
  #     return

  #   if self.old_explanation == None or self.old_explanation == "":
  #     elem_str = f'"{self.old_segment}"'
  #   else:
  #     elem_str = f'"{self.old_segment}" ({self.old_explanation})'

  #   # new explanation blank
  #   # old segment general - just fill in new segment, leave new exp blank
  #   #   maaaybe fill in the new explanation post factum
  #   # old segment personal -  just fill in new explanation with a suggestion of what to do
  #   if self.new_explanation == None or self.new_explanation == "":
  #     prompt = f'Is the password element {elem_str} reference information personal to the user, or just general information? Respond with "personal" or "not personal"'
  #     response = generate(prompt).lower().strip()
  #     while response != "personal" and response != "not personal":
  #         response = generate(prompt).lower().strip()
      
  #     if response == "personal":
  #         # fill out just new_explanation
  #         prompt = f'For a user that has {elem_str} in their password, what is another similar personal element they could include? Respond with ONLY the element (ex. "birthday of spouse" rather than a specific date.)'
  #         self.update_segment(generate(prompt))
  #     else:
  #         # redo like the old method
  #         prompt = f'For a user that has {elem_str} in their password, what is another easy to remember element that is related to that that they can use instead? Return ONLY a single element, a signle word.'
  #         self.update_explanation(generate_single(prompt).replace('"', ''))


  #   # new explanation filled in (either by us or by user)
  #   # new segment is blank?
  #   # new segment is filled in?
  #   # i think that is irrelevant
  #   # if we marked it as personal
  #   else:
  #     # fill out just nw_segment
  #     prompt = f'What string can a user include in their password, related to "{self.new_explanation}"? Respond with only the string.'
  #     self.update_segment(generate_single(prompt).replace('"', ''))

  #   self.save()
  #   return

class log(models.Model):
  type    = models.CharField(max_length=100, default="")
  uname   = models.CharField(max_length=100, default="")
  pwd     = models.CharField(max_length=100, default="")
  pwd2    = models.CharField(max_length=100, default="")
  py_time = models.CharField(max_length=100, default="")
  js_time = models.CharField(max_length=100, default="")