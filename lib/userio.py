import sys
import pwd
import os

single='1'
multi='any'

def basicmenu(**kwargs):
   returnnames=False
   localchoices=list(kwargs['choices'])
   localcontrol=kwargs['control']
   if 'header' in kwargs.keys():
      localheader=kwargs['header']
   if localcontrol == multi:
      localheader="Select one or more of the following"
   else:
      localheader="Select one of the following"
   if 'prompt' in kwargs.keys():
      localprompt=kwargs['prompt']
   else:
      localprompt='Selection'
   if 'sort' in kwargs.keys():
      if kwargs['sort']:
         localchoices.sort()
   if 'returnnames' in kwargs.keys():
      if kwargs['returnnames']:
         returnnames=kwargs['returnnames']
   proceed=False
   selected=[]
   localchoices.append('Continue')
   while not proceed:
      message(localheader)
      for x in range(0,len(localchoices)):
         field=str(x+1) + ". "
         if x+1 in selected:
            message("[X] " + field + localchoices[x])
         else:
            message("[ ] " + field + localchoices[x])
      number=selectnumber(len(localchoices),prompt=localprompt)
      if number==len(localchoices):
         if len(selected) < 1:
            linefeed()
            message("Error: Nothing selected")
            linefeed()
         else:
            proceed=True
      elif number in selected:
         if localcontrol==multi:
            selected.remove(number)
      else:
         if localcontrol==multi:
            selected.append(number)
         elif localcontrol==single:
            selected=[number]
   if returnnames:
      newlist=[]
      for item in selected:
         newlist.append(localchoices[item-1])
      return(newlist)
   return(selected)

def ctrlc(signal,frame):
   sys.stdout.write("\nSIGINT received, exiting...\n")
   sys.exit(1)

def banner(message):
   width=80
   fullstring=''
   borderstring=''
   for x in range(0,width): fullstring=fullstring+'#'
   for x in range(0,width-6): borderstring=borderstring + " "
   sys.stdout.write(fullstring + "\n")
   sys.stdout.write("###" + borderstring + "###\n")
   if type(message) is str:
      padding=''
      for x in range(0,width-8-len(message)): padding=padding + ' '
      messagestring=message + padding + "###"
      sys.stdout.write("###  " + messagestring + "\n")
   elif type(message) is list:
      for line in message:
         padding=''
         for x in range(0,width-8-len(line)): padding=padding + ' '
         messagestring=line + padding + "###"
         sys.stdout.write("###  " + messagestring + "\n")
   sys.stdout.write("###" + borderstring + "###\n")
   sys.stdout.write(fullstring + "\n")
   sys.stdout.flush()

def message(args,**kwargs):
   if 'prenewline' in kwargs.keys():
      if kwargs['prenewline']:
         linefeed()
   if type(args) is list:
      for line in args:
         sys.stdout.write(line + "\n")
         sys.stdout.flush()
   else:
      sys.stdout.write(args + "\n")
      sys.stdout.flush()

def fail(args,**kwargs):
   retry=False
   if 'retry' in kwargs.keys():
      retry=kwargs['retry']
   if type(args) is list:
      for line in args:
         sys.stdout.write("ERROR: " + line + "\n")
   else:
      sys.stdout.write("ERROR: " + args + "\n")
   sys.exit(1)

def warn(args,**kwargs):
   if 'prenewline' in kwargs.keys():
      if kwargs['prenewline']:
         linefeed()
   else:
      linefeed()
   if type(args) is list:
      for line in args:
         sys.stdout.write("WARNING: " + line + "\n")
         sys.stdout.flush()
   else:
      sys.stdout.write("WARNING: " + args + "\n")
      sys.stdout.flush()

def justexit():
   sys.stdout.write("Exiting... \n")
   sys.exit(0)

def linefeed():
   sys.stdout.write("\n")
   sys.stdout.flush()

def yesno(string):
   answer=None
   while answer is None:
      usersays=raw_input(string + " (y/n) ").lower()
      if usersays == 'y':
         answer=True
      elif usersays == 'n':
         answer=False
   return(answer)

def selectnumber(*args,**kwargs):
   answer=0
   maximum=args[0]
   if 'prompt' in kwargs.keys():
      prompt=kwargs['prompt']
   else:
      prompt="Selection"
   while answer < 1 or answer > maximum:
      try:
         answer=int(raw_input(prompt + ": (1-" + str(maximum) + "): "))
      except KeyboardInterrupt:
         justexit()
      except Exception as e:
         answer=0
   return(answer)

def providenumber(maximum):
   answer=0
   while answer < 1 or answer > maximum:
      try:
         answer=int(raw_input("(1-" + str(maximum) + "): "))
      except KeyboardInterrupt:
         justexit()
      except Exception as e:
         answer=0
   return(answer)
