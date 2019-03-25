import sys
import os
import userio
import subprocess
import random
import pwd
import grp

def forcemkdir(path,**kwargs):
   quiet=True

   if 'quiet' in kwargs.keys():
      quiet=kwargs['quiet']
   if not os.path.exists(path):
      if not quiet:
         userio.message("Creating directory: " + path)
      try:
         os.makedirs(path)
      except:
         if not quiet:
            userio.message("Unable to create directory: ")
            return(False)
   else:
      if not quiet:
         userio.message("Directory already exists: " + path)

   if 'user' in kwargs.keys():
      if kwargs['user'] is None:
         if not quiet:
            userio.message("User passed was 'None'")
            return(False)

      if not quiet:
         userio.message("Setting user ownership of " + path + " to " + kwargs['user'])
      try:
         newuid=pwd.getpwnam(kwargs['user']).pw_uid
      except:
         if not quiet:
            userio.message("Unknown user: " + kwargs['user'])
            return(False)
      try:
         os.chown(path,newuid,-1)
      except:
         if not quiet:
            userio.message("Unable to set user of " + path + " to " + kwargs['user'])
            return(False)
      
   if 'group' in kwargs.keys():
      if kwargs['group'] is None:
         if not quiet:
            userio.message("Group passed was 'None'")
            return(False)
      if not quiet:
         userio.message("Setting group ownership of " + path + " to " + kwargs['group'])
      try:
         newgid=grp.getgrnam(kwargs['group']).gr_gid
      except:
         if not quiet:
            userio.message("Unknown group: " + kwargs['group'])
            return(False)
      try:
         os.chown(path,-1,newgid)
      except:
         if not quiet:
            userio.message("Unable to set group of " + path + " to " + kwargs['group'])
            return(False)
   
   if 'mode' in kwargs.keys():
      try:
         octalmode=int(str(kwargs['mode']),8)
      except:
         if not quiet:
            userio.message("Invalid mode: " + str(kwargs['mode']))
            return(False)
      if not quiet:
         userio.message("Setting mode of " + path + " to " + str(kwargs['mode']))
      try:
         os.chmod(path,octalmode)
      except:
         if not quiet:
            userio.message("Unable to set mode of " + path + " to " + str(kwargs['mode']))
            return(False)
   return(True)

def getpathinfo(path):
   resultdict={}
   if os.path.isdir(path):
      resultdict['ISDIR']=True
      resultdict['ISFILE']=False
   elif os.path.isfile(path):
      resultdict['ISDIR']=False
      resultdict['ISFILE']=True
   else:
      resultdict['ISDIR']=False
      resultdict['ISFILE']=False
      return(resultdict)
   pathdata=os.stat(path)
   resultdict['UID']=pathdata.st_uid
   resultdict['GID']=pathdata.st_gid
   resultdict['USER']=pwd.getpwuid(pathdata.st_uid).pw_name
   resultdict['GROUP']=grp.getgrgid(pathdata.st_gid).gr_name
   resultdict['PERMS']=oct(pathdata.st_mode & 0777)
   return(resultdict)

def checkfileprotection(filepath):
   servicename='checkfileprotection'
   returncode=1
   try:
      tempfilehandle=open(filepath,soc.READ)
      userio.message(servicename,"Found file at " + filepath)
   except:
      userio.message(servicename,"Failed to open " + filepath + " for reading")
      return(0)
   if os.stat(filepath).st_uid == 0:
      userio.message(servicename,"File " + filepath + " is owned by root")
   else:
      userio.message(servicename,"File " + filepath + " not owned by root")
      return(0)
   mask=oct(os.stat(filepath).st_mode & 0777)
   if mask == '0600':
      userio.message(servicename,"File " + filepath + " has permissions 0600")
   else:
      userio.message(servicename,"File " + filepath + " is not secure")
      return(0)
   return(returncode)

def decryptpath(encryptedpath):
   servicename='decrypt'
   fh=open(encryptedpath,'rb+')
   encrypteddata=fh.read()[:-32]
   fh.seek(-32,2)
   iv=fh.read(32)
   fh.close()
   mypath="/bin:/usr/bin:/usr/local/bin:"
   myldlibrarypath="/lib"
   myenv={"PATH": mypath, "LD_LIBRARY_PATH": myldlibrarypath}
   procargs=['openssl','enc','-d','-aes-256-cbc','-z','-kfile',soc.keyfilelocation,'-iv',iv]
   sslprocess=subprocess.Popen(procargs,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.PIPE, shell=False, env=myenv)
   out, err = sslprocess.communicate(input=encrypteddata)
   if len(err) > 0:
      for line in out.split("\n"): userio.message(servicename,"  stdout: " + line)
      for line in err.split("\n"): userio.message(servicename,"  stderr: " + line)
      userio.messageanddie("Fatal openssl decryption error")
   return(out)

def encryptpath(plaintextstring,encryptedpath):
   if not checkfile(encryptedpath,soc.WRITE) == soc.FILEOK:
      releaselock()
      messageanddie ('Could not open file for writing' + encryptedpath)
   iv=''.join(random.choice('0123456789abcdef') for _ in range(32))
   mypath="/bin:/usr/bin:/usr/local/bin:"
   myldlibrarypath="/lib"
   myenv={"PATH": mypath, "LD_LIBRARY_PATH": myldlibrarypath}
   procargs=['openssl','enc','-aes-256-cbc','-z','-kfile',soc.keyfilelocation,'-iv',iv,'-out',encryptedpath]
   sslprocess=subprocess.Popen(procargs,stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.PIPE,shell=False, env=myenv)
   out, err = sslprocess.communicate(input=plaintextstring)
   if len(out) > 0 or len(err) > 0:
      message("Fatal openssl encryption error")
      for line in out.split("\n"): message("   stdout: " + line)
      for line in err.split("\n"): message("   stderr: " + line)
      sys.exit(1)
   fh=open(encryptedpath,'ab')
   fh.write(iv)
   fh.close()
   return(0)

