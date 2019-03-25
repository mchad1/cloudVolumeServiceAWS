import os
import pwd
from doprocess import doprocess
from dosqlplus import dosqlplus

oratablocation='/etc/oratab'
abort='abort'
mount='mount'
nomount='nomount'

def homeanduser(oraclesid,kwargs):
   if 'home' in kwargs.keys():
      oraclehome=kwargs['home']
   else:
      oraclehome=getoraclehome(oraclesid)
      if oraclehome is None:
         return({'RESULT':1,'STDOUT':[],'STDERR':['Unable to get ORACLE_HOME for ' + oraclesid]})

   if 'user' in kwargs.keys():
      oracleuser=kwargs['user']
   else:
      oracleuser=getoracleuser(oraclehome)
      if oracleuser is None:
         return({'RESULT':1,'STDOUT':[],'STDERR':['Unable to get Oracle user for ' + oraclehome]})
   return oracleuser, oraclehome


def getoraclehome(localsid):
   try:
      oratablines=open(oratablocation, 'r').read().splitlines()
   except:
      return(None)
   for line in oratablines:
      oratabfields = line.split(':')
      if oratabfields[0] == localsid:
         return(oratabfields[1])
   return(None)

def startup(oraclesid,**kwargs):
   try:
       oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
       homeanduser(oraclesid,kwargs)
       exit()
   startuptype=''

   if 'method' in kwargs.keys():
      startuptype=kwargs['method']
   cmd='startup ' + startuptype+ ';'
   out=dosqlplus(oraclesid,cmd,user=oracleuser,home=oraclehome)
   if out['RESULT'] > 0:
      return({'RESULT':1,'STDOUT':out['STDOUT']})
   else:
      for line in out['STDOUT']:
         if line == 'Database opened.' and startuptype=="":
            return({'RESULT':0,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
         elif line == 'Database mounted.' and startuptype=="mount":
            return({'RESULT':0,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
         elif line[-24:] == 'ORACLE instance started.' and startuptype=="mount":
            return({'RESULT':0,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})

def gettableinfo(oraclesid,**kwargs):
   try:
       oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
       homeanduser(oraclesid,kwargs)

   cmds=[]
   cmds.append("SELECT a.tablespace_name Tablespace,")
#   cmds.append("ROUND(( 1 - ( fbytes / tbytes ) ) * 100, 1) Percent_Used,")
   cmds.append("ROUND(tbytes / 1024 / 1024, 1) MB_Total")
#   cmds.append("ROUND(fbytes / 1024 / 1024, 1) MB_Free,")
#   cmds.append("ROUND(( tbytes - fbytes ) / 1024 / 1024, 1) MB_Used")
   cmds.append("FROM (SELECT tablespace_name,")
   cmds.append("SUM(bytes) tbytes")
   cmds.append("FROM dba_data_files")
   cmds.append("GROUP BY tablespace_name")
   cmds.append("UNION ALL")
   cmds.append("SELECT tablespace_name,")
   cmds.append("SUM(bytes) tbytes")
   cmds.append("FROM dba_temp_files")
   cmds.append("GROUP BY tablespace_name) a;")
#   cmds.append("left outer join (SELECT tablespace_name,")
#   cmds.append("SUM(bytes) fbytes")
#   cmds.append("FROM dba_free_space")
#   cmds.append("GROUP BY tablespace_name")
#   cmds.append("UNION ALL")
#   cmds.append("SELECT tablespace_name,")
#   cmds.append("SUM(user_bytes) fbytes")
#   cmds.append("FROM dba_temp_files")
#   cmds.append("GROUP BY tablespace_name) b")
#   cmds.append("ON a.tablespace_name = b.tablespace_name;")
   out=dosqlplus(oraclesid,cmds,user=oracleuser,home=oraclehome)
   if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
      return(None)
   else:
      tableinfo={}
      for line in out['STDOUT']:
         try:
            tablespacename,mbtotal=line.split()
            tableinfo[tablespacename]={'TOTALMB':int(mbtotal)}
         except:
            return(None)
      return(tableinfo)

def shutdown(oraclesid,**kwargs):
   try:
       oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
       homeanduser(oraclesid,kwargs)
       exit()
   shutdowntype='immediate'

   if 'method' in kwargs.keys():
      startuptype=kwargs['method']
   cmd='shutdown ' + shutdowntype + ';'
   out=dosqlplus(oraclesid,cmd,user=oracleuser,home=oraclehome)
   if out['RESULT'] > 0:
      return({'RESULT':1,'STDOUT':out['STDERR']})
   else:
      for line in out['STDOUT']:
         if line == 'ORACLE instance shut down.':
            return({'RESULT':0,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})


def noarchivelogmode(oraclesid,**kwargs):
   try:
       oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
       homeanduser(oraclesid,kwargs)
       exit()

   current=checkarchivelogmode(oraclesid)

   if current['RESULT'] > 0:
      return({'RESULT':1,'STDOUT':current['STDOUT'],'STDERR':current['STDERR']})
   elif current['ENABLED'] == True:
      out=shutdown(oraclesid,home=oraclehome,user=oracleuser)
      if out['RESULT'] > 0:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=startup(oraclesid,home=oraclehome,user=oracleuser,method='mount')
      if out['RESULT'] > 0:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=dosqlplus(oraclesid,'alter database noarchivelog;',user=oracleuser,home=oraclehome)
      if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=dosqlplus(oraclesid,'alter database open;',user=oracleuser,home=oraclehome)
      if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      return({'RESULT':0,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
   else:
      return({'RESULT':0,'STDOUT':current['STDOUT'],'STDERR':current['STDERR']})

def enter_hotbackupmode(oraclesid,**kwargs):
   try:
      oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
      homeanduser(oraclesid,kwargs)
      exit()
   current=checkarchivelogmode(oraclesid)
   if current['ENABLED'] == True:
      archivelogpath=current['PATH']
      #Check to see if already in hotbackup mode before beginning
      out=checkbackup(oraclehome,oraclesid,oracleuser)
      #If in hotbackup mode already, end it before starting again and if it still doesn end, quite
      if len(out['STDOUT']) is not 0:
         out=endbackup(oraclehome,oraclesid,oracleuser)
         #Check to see if STILL in hotbackup mode before, if YES print logs in hotbackup mode and quit
         out=checkbackup(oraclehome,oraclesid,oracleuser)
         if len(out['STDOUT']) is not 0:
            for line in out['STDOUT']:
               print(line)
      #Enter hot backup mode      
      out=beginbackup(oraclehome,oraclesid,oracleuser)
      #Check to see if tablespaces are in hotbackup mode, capture the tablepaces
      out=checkbackup(oraclehome,oraclesid,oracleuser)
      if len(out['STDOUT']) is not 0:
         for line in out['STDOUT']:
            print(line)
       
def leave_hotbackupmode(oraclesid,**kwargs):
   try:
      oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
      homeanduser(oraclesid,kwargs)
      exit()
   current=checkarchivelogmode(oraclesid)
   if current['ENABLED'] == True:
      archivelogpath=current['PATH']
      #Check to see if already in hotbackup mode before beginning
      out=checkbackup(oraclehome,oraclesid,oracleuser)
      #If in hotbackup mode already, end it before starting again and if it still doesn end, quite
      if len(out['STDOUT']) is not 0:
         out=endbackup(oraclehome,oraclesid,oracleuser)
         #Check to see if STILL in hotbackup mode before, if YES print logs in hotbackup mode and quit
         out=checkbackup(oraclehome,oraclesid,oracleuser)
         if len(out['STDOUT']) is not 0:
            for line in out['STDOUT']:
               print(line)

def recover_database(oraclesid,**kwargs):
   try:
      oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
      homeanduser(oraclesid,kwargs)
      exit()
   #Shutdown the database, aborting all current sessions, etc...
   #If in hotbackup mode already, end it before starting again and if it still doesn end, quite
   startup = dosqlplus(oraclesid,"startup mount;",user=oracleuser,home=oraclehome)
   if len(startup['STDOUT']) is not 0:
      for line in startup['STDOUT']:
         print(line)
   recover = dosqlplus(oraclesid,"recover automatic;",user=oracleuser,home=oraclehome)
   if len(recover['STDOUT']) is not 0:
      for line in recover['STDOUT']:
         print(line)
   open_db = dosqlplus(oraclesid,"alter database open;",user=oracleuser,home=oraclehome)
   if len(open_db['STDOUT']) is not 0:
      for line in out['STDOUT']:
         print(line)




def shutdown_abort(oraclesid,**kwargs):
   try:
      oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
      homeanduser(oraclesid,kwargs)
      exit()
   #Shutdown the database, aborting all current sessions, etc...
   #If in hotbackup mode already, end it before starting again and if it still doesn end, quite
   abort = dosqlplus(oraclesid,"shutdown abort;",user=oracleuser,home=oraclehome)
   if len(abort['STDOUT']) is not 0:
      for line in abort['STDOUT']:
         print('%s' % (line))

def beginbackup(oraclehome,oraclesid,oracleuser):
   begin = dosqlplus(oraclesid,"alter database begin backup;",user=oracleuser,home=oraclehome)
   if len(begin['STDOUT']) is not 0:
      for line in begin['STDOUT']:
         print('%s' % (line))
   print('Executing "alter database begin backup;" against oracle sid: %s' % (oraclesid))

def endbackup(oraclehome,oraclesid,oracleuser):
   end = dosqlplus(oraclesid,"alter database end backup;",user=oracleuser,home=oraclehome)
   if len(end['STDOUT']) is not 0:
      for line in end['STDOUT']:
         print('%s' % (line))
   print('Executing "alter database end backup;" against oracle sid: %s' % (oraclesid))

   roll = dosqlplus(oraclesid,"alter system archive log current;",user=oracleuser,home=oraclehome)
   if len(roll['STDOUT']) is not 0:
      for line in roll['STDOUT']:
         print('%s' % (line))
   print('Executing "alter system archive log current;" against oracle sid: %s' % (oraclesid))

    

def checkbackup(oraclehome,oraclesid,oracleuser):
   return dosqlplus(oraclesid,"select v$datafile.name\
                               from v$backup inner join v$datafile on v$datafile.file# = v$backup.file# \
                               where v$backup.status = 'ACTIVE';",user=oracleuser,home=oraclehome)

def checkarchivelogmode(oraclesid,**kwargs):
   try:
       oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
       homeanduser(oraclesid,kwargs)
       exit()

   returndict={}
   returndict['ENABLED']=None
   returndict['PATH']=None
   returndict['RESULT']=1
   returndict['STDOUT']=[]
   returndict['STDERR']=[]
   out=dosqlplus(oraclesid,"archive log list;",user=oracleuser,home=oraclehome)
   if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
      return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
   else:
      for line in out['STDOUT']:
         #print(line)
         if line[:17] == 'Database log mode':
            if line.split()[3].rstrip() + line.split()[4].rstrip() == "ArchiveMode":
               returndict['ENABLED']=True
               returndict['RESULT']=0
            else:
               returndict['ENABLED']=False
               returndict['RESULT']=0
         elif line[:19] == 'Archive destination':
            returndict['PATH']=line.split()[2].rstrip()
      return(returndict)

def setarchivelogmode(oraclesid,path,**kwargs):
   try:
       oracleuser, oraclehome = homeanduser(oraclesid,kwargs)
   except:
       homeanduser(oraclesid,kwargs)
       exit()

   from fileio import getpathinfo
   force=False

   if 'force' in kwargs.keys():
      force=kwargs['force']

   if force:
      if not os.path.isdir(path):
         try:
            os.makedirs(path)
         except:
            return({'RESULT':1,'STDOUT':[],'STDERR':["Unable to create path: " + path]})
      oracleuid=pwd.getpwnam(oracleuser).pw_uid
      oraclegid=pwd.getpwnam(oracleuser).pw_gid
      try:
         os.chown(path,oracleuid,oraclegid)
      except:
         return({'RESULT':1,'STDOUT':[],'STDERR':["Unable to set ownership of " + path + " to " + oracleuser]})
   
   checkaccess=getpathinfo(path)
   if not checkaccess['ISDIR']:
      return({'RESULT':1,'STDOUT':[],'STDERR':['Path ' + path + ' does not exist']})
   elif not checkaccess['USER'] == oracleuser:
      return({'RESULT':1,'STDOUT':[],'STDERR':['Oracle user does not own the archive log path']})

   current=checkarchivelogmode(oraclesid)
   if current['RESULT'] > 0:
      return({'RESULT':1,'STDOUT':current['STDOUT'],'STDERR':out['STDERR']})
   elif current['ENABLED'] == False or not current['PATH'] == path:
      out=dosqlplus(oraclesid,"alter system set log_archive_dest='" + path + "' scope=spfile;",user=oracleuser,home=oraclehome)
      if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=shutdown(oraclesid,home=oraclehome,user=oracleuser)
      if out['RESULT'] > 0:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=startup(oraclesid,home=oraclehome,user=oracleuser,method='mount')
      if out['RESULT'] > 0:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=dosqlplus(oraclesid,"alter database archivelog;",user=oracleuser,home=oraclehome)
      if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      out=dosqlplus(oraclesid,"alter database open;",user=oracleuser,home=oraclehome)
      if out['RESULT'] > 0 or out['ERRORFLAG'] > 1:
         return({'RESULT':1,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
      return({'RESULT':0,'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
   else:
      return({'RESULT':0,'STDOUT':current['STDOUT'],'STDERR':current['STDERR']})

def getoraclebase(oraclehome):
   oracleuser=getoracleuser(oraclehome)
   if oracleuser is None:
      return(None)
   out=doprocess(oraclehome + "/bin/orabase",user=oracleuser,env={'ORACLE_HOME':oraclehome,'LIB':oraclehome + '/lib'})
   if out['RESULT'] == 0:
      if os.path.exists(out['STDOUT'][-1]):
         return(out['STDOUT'][-1])
      else:
         return(None)
   else:
      return(None)

def getoracleuser(oraclehome):
   try:
      oracleuid=os.stat(oraclehome).st_uid
      oracleuser=pwd.getpwuid(oracleuid).pw_name
      return(oracleuser)
   except:
      return(None)

def getoratab():
   oratabdict={}
   oratabdict['COMMENTS']=[]
   oratabdict['SIDS']={}
   try:
      lines=open('/etc/oratab','r').readlines()    
   except:
      return(None)
   for line in lines:
      if line[0] == '#':
         oratabdict['COMMENTS'].append(line)
      else:
         try:
            sid,home,startup=line.split(':')
            oratabdict['SIDS'][sid]={'HOME':home,'STARTUP':startup}
         except:
            pass
   return(oratabdict)

def add2oratab(oraclehome,sid):
   try:
      lines=open('/etc/oratab','r').readlines()
   except:
      return({'RESULT':1})
   neworatab=open('/etc/oratab','w')
   for line in lines:
      if not line[:len(sid)+1]==sid + ':':
         neworatab.write(line)
   neworatab.write(sid + ":" + oraclehome + ":N\n")
   neworatab.close()
   return({'RESULT':0})

def deletedatabase(oraclesid,**kwargs):
   if 'home' in kwargs.keys():
      oraclehome=kwargs['home']
   else:
      oraclehome=getoraclehome(oraclesid)
      if oraclehome is None:
         return({'RESULT':1,'STDOUT':[],'STDERR':['Unable to get ORACLE_HOME for ' + oraclesid]})

   if 'user' in kwargs.keys():
      oracleuser=kwargs['user']
   else:
      oracleuser=getoracleuser(oraclehome)
      if oracleuser is None:
         return({'RESULT':1,'STDOUT':[],'STDERR':['Unable to get Oracle user for ' + oraclehome]})

   if 'password' in kwargs.keys():
      deletepwd=kwargs['password']
   else:
      deletepwd='oracle'

   out=doprocess("dbca -silent -deleteDatabase -sourceDB " + oraclesid,input="oracle",user=oracleuser,env={'PATH':oraclehome+"/bin",'ORACLE_HOME':oraclehome,'ORACLE_SID':oraclesid},printstdout=True)

   return({'RESULT':out['RESULT'],'STDOUT':out['STDOUT'],'STDERR':out['STDERR']})
