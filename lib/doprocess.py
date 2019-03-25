import os
import subprocess
import pwd
import grp
import userio

def isroot():
   if os.geteuid() == 0:
      return(True)
   else:
      return(False)

def rootonly():
   if not isroot():
      userio.fail("User must be root")

def doprocess(command,**kwargs):
   passkwargs={'bufsize':1,'stdin':subprocess.PIPE,'stdout':subprocess.PIPE,'stderr':subprocess.PIPE,'shell':False}
   commandblock=''
   cmdargs=[]
   printstdout=False
   retryable=False
   showchange=False
   tryagain=True
   stdin=None
   returndict={}
   mypath="/bin:/usr/bin:/usr/local/bin"
   myldlibrarypath="/lib"
   myenv={"PATH": mypath, "LD_LIBRARY_PATH": myldlibrarypath}
   mylist=command.split(' ')
   for item in mylist:
      cmdargs.append(item)
   if 'env' in kwargs.keys():
      for key in kwargs['env'].keys():
         if key in myenv.keys():
            myenv[key]=myenv[key]+":"+kwargs['env'][key]
         else:
            myenv[key]=kwargs['env'][key]
   passkwargs['env']=myenv
   if 'user' in kwargs.keys():
      useraccount=kwargs['user']
      if 'showchange' in kwargs.keys():
         passkwargs['preexec_fn']=changeuser(useraccount,showchange=kwargs['showchange'])
      else:
         passkwargs['preexec_fn']=changeuser(useraccount,showchange=False)
   if 'printstdout' in kwargs.keys():
      printstdout=kwargs['printstdout']
   if 'retry' in kwargs.keys():
      retryable=kwargs['retry']
   if 'input' in kwargs.keys():
      if type(kwargs['input']) is str:
         stdin=kwargs['input']
         stdin=stdin + "\n"
      elif type(kwargs['input']) is list:
         stdin=''
         for line in kwargs['input']:
            stdin=stdin + line
            if not stdin[-1] == "\n":
               stdin=stdin + "\n"
   if 'cwd' in kwargs.keys():
      passkwargs['cwd']=kwargs['cwd']
   while tryagain:
      tryagain=False
      stdout=[]
      stderr=[]
      resultcode=None
      
      try:
         cmd=subprocess.Popen(cmdargs,**passkwargs)
      except:
         resultcode=1

      if resultcode is None:
         if printstdout:
            if not stdin is None:
               cmd.stdin.write(stdin)
            while cmd.poll() is None:
               nextline=cmd.stdout.readline().rstrip()
               if len(nextline) > 0:
                  userio.message(nextline)
                  stdout.append(nextline)
            remainder=cmd.stdout.readlines()
            for nextline in remainder:
               if len(nextline) > 0:
                  userio.message(nextline)
                  stdout.append(nextline)
            stderr=cmd.stderr.readlines()
         else:
            if not stdin is None:
               cmdout,cmderr=cmd.communicate(stdin)
            else:
               cmdout,cmderr=cmd.communicate()
            lines=cmdout.splitlines()
            for line in lines:
               if len(line) > 0:
                  stdout.append(line)
            lines=cmderr.splitlines()
            for line in lines:
               if len(line) > 0:
                  stderr.append(line)
    
         resultcode=cmd.returncode
      
      if retryable and resultcode > 0:
         userio.warn("Errors encountered during '" + command + "'")
         for line in stdout:
            userio.message("STDOUT: " + line)
         for line in stderr:
            userio.message("STDERR: " + line)
         tryagain=userio.yesno("Retry?")

   returndict['STDOUT']=stdout
   returndict['STDERR']=stderr
   returndict['RESULT']=resultcode
   return(returndict)


def changeuser(user,**kwargs):
   if 'showchange' in kwargs.keys():
      showchange=kwargs['showchange']
   else:
      showchange=False
   userinfo=pwd.getpwnam(user)
   newuid=userinfo.pw_uid
   newgid=userinfo.pw_gid
   grouplist=[newgid]
   allgroups=grp.getgrall()
   for item in allgroups:
      if user in item[3]:
         grouplist.append(item[2])
   def set_ids():
      if showchange:
         userio.message("Changing GID to " + str(newgid))
      os.setgid(newgid)
      if showchange:
         userio.message("Changing group memberships to " + str(grouplist))
      os.setgroups(grouplist)
      if showchange:
         userio.message("Changing user to " + user) 
      os.setuid(newuid)
   return set_ids
