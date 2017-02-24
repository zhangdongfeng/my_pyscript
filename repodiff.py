#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import os, sys
import re
import codecs
import subprocess
import shutil
import time
import string

from optparse import OptionParser

reload(sys)
sys.setdefaultencoding('utf-8')

REVISION_RE=r"revision=\"(\S+)\"";
PROJECT_NAME_RE=r"name=\"(\S+)\"";
PROJECT_PATH_RE=r"path=\"(\S+)\"";
REMOTE_FETCH_RE=r"fetch=\"(\S+)\"";
REMOTE_NAME_RE=r"name=\"(\S+)\"";
REMOTE_REVIEW_RE=r"review=\"(\S+)\"";
DEFAULT_REMOTE_RE=r"remote=\"(\S+)\"";

REMOTE_TAG_RE=r"<remote[^>]*>";
DEFAULT_TAG_RE=r"<default[^>]*>";
PROJECT_TAG_RE=r"<project[^>]*>";

COMMITID_RE=r"commit:(\S+) date:(\S+) subject:(.*) author:(.*)\n";

FILESTATUS_RE=r"\b([M|C|R|A|D|U])\s+(\S+)\s*";

class RepoProject:
    def __init__(self, xml, basepath):
        self.xml = xml;
        self.basepath = basepath;
        self.manifest = {};
        self.manifest["projects"]=[];
        self.parserManifestXml(self.xml);


    def parserManifestXml(self,xml):
        lines="";
        try:
            fp = open(xml, 'rb');
            manifestData = fp.read();
            fp.close();
        except Exception,e:
            print e;
            
        remoteMatch = re.search(REMOTE_TAG_RE, manifestData);
        defaultMatch = re.search(DEFAULT_TAG_RE, manifestData);
        projectMatch = re.findall(PROJECT_TAG_RE, manifestData); 

        remoteString = remoteMatch.group()
        defaultString = defaultMatch.group()
        projectStrings = projectMatch


        fetch = re.search(REMOTE_FETCH_RE, remoteString);
        name = re.search(REMOTE_NAME_RE, remoteString);
        review = re.search(REMOTE_REVIEW_RE, remoteString);
        self.manifest["remote"] = {
            "fetch":fetch.groups()[0],
            "review":review.groups()[0],
            "name":name.groups()[0]
        }; 

        remote = re.search(DEFAULT_REMOTE_RE, defaultString);
        revision = re.search(REVISION_RE, defaultString);
        self.manifest["default"] = {
            "remote":remote.groups()[0],
            "revision":revision.groups()[0],
        }; 

        for s in projectStrings:
            prj = re.search(PROJECT_NAME_RE, s);
            path = re.search(PROJECT_PATH_RE, s);
            revision = re.search(REVISION_RE, s);
            if prj:
                prj = prj.groups()[0];
            else:
                prj = None;
                
            if path:
                path =  path.groups()[0];
            else:
                path = None;

            if revision:
                revision =  revision.groups()[0];
            else:
                revision = None;

            try:
                p = self.manifest["projects"];
            except:
                self.manifest["projects"]=[];

            if path is None:
                path = prj;

            if prj:
                self.manifest["projects"].append((prj,path, revision));


    def getProjects(self):
        try:
            return self.manifest["projects"];
        except:
            return [];

    def getProjectPath(self, path):
        return os.path.join(self.basepath,path);

    def isValidPath(self,path):
        valid = False;
        for p in self.manifest["projects"]:
            if path == p[1]:
                valid = True;
                break;
        return valid;

    def getManifest(self):
        return self.manifest;


class GitOperation(object):
    def __init__(self, project):
        self.repoProject = project;
        self.projects = self.repoProject.getProjects()

    def execGitCmd(self, cwd, cmd):
        try:
            env = os.environ.copy()
            proc = subprocess.Popen(cmd, 
                    cwd=cwd,
                    stdout = subprocess.PIPE, 
                    stderr = subprocess.PIPE,
                    env=env
                    )
            out = proc.stdout.read()
            err = proc.stderr.read()
            proc.stdout.close() 
            proc.stderr.close() 
        except Exception,e:
            print "execGitCmd Error: cmd=%s, cwd=%s" % (str(cmd), str(cwd))
            return "";

        if err:
            print "Error: cmd="+str(cmd)+ ", cwd= "+cwd+",   errorinfo=" + err;
        return out,err;
    
    def getCommitPatch(self, path, commit):
        if not self.repoProject.isValidPath(path):
            print "invalid path" +path
            return None;

        args = "--pretty=format:%H";

        cmd = ['git', 'log', "-1", "-p", args, commit];
        print cmd

        cwd = self.repoProject.getProjectPath(path);
        print cwd

        outdata,err = self.execGitCmd(cwd, cmd);
        print outdata
        if outdata:                        
            return outdata;
        else:
            return None;


    def getTags(self, path):
        if not self.repoProject.isValidPath(path):
            print "invalid path" +path
            return None;

        args ="--pretty=format:commit:%H date:%at subject:%s%n"

        cmd = ['git', 'tag'];

        cwd = self.repoProject.getProjectPath(path);

        outdata,err = self.execGitCmd(cwd, cmd);

        if outdata:                        
            return outdata.splitlines();
        else:
            return [];

    def isValidTag(self,path, tags, t):
        return t in tags;


    def getCommitInfo(self, path, commit):
        if not self.repoProject.isValidPath(path):
            print "invalid path" +path
            return None;

        args ="--pretty=format:commit:%H date:%at subject:%s%n"

        cmd = ['git', 'log', args, commit];

        cwd = self.repoProject.getProjectPath(path);

        outdata,err = self.execGitCmd(cwd, cmd);

        if outdata:                        
            return outdata;
        else:
            return None;

    def getCommitsByRev(self, path, startrev, endrev):
        if not self.repoProject.isValidPath(path):
            print "invalid path" +path
            return None,isNewGitProject;

        isNewGitProject = False;
        
        if not endrev:
            print endrev+" is not exist in "+path
            return None,isNewGitProject


        args ="--pretty=format:commit:%H date:%at subject:%s author:%an%n"

        if startrev:
            cmd = ['git', 'log', args, startrev+".."+endrev];
        else:
            cmd = ['git', 'log', args, endrev];
            isNewGitProject = True


        cwd = self.repoProject.getProjectPath(path);

        outdata,err = self.execGitCmd(cwd, cmd);

        if err:
            cmd = ['git', 'log', args, endrev];
            isNewGitProject = True
            outdata,err = self.execGitCmd(cwd, cmd);

        if not outdata:
            return None,isNewGitProject;
        else:
            c = re.findall(COMMITID_RE,outdata);
            if c:
                return c, isNewGitProject;
            else:
                return None;

    def getCommitsByTag(self, path, starttag, endtag):
        if not self.repoProject.isValidPath(path):
            print "invalid path" +path
            return None,isNewGitProject;

        isNewGitProject = False;
        tags = self.getTags(path);
        
        if not self.isValidTag(path, tags, endtag):
            print endtag+" is not exist in "+path
            return None,isNewGitProject


        args ="--pretty=format:commit:%H date:%at subject:%s author:%an%n"

        if self.isValidTag(path, tags, starttag):
            cmd = ['git', 'log', args, starttag+".."+endtag];
        else:
            cmd = ['git', 'log', args, endtag];
            isNewGitProject = True


        cwd = self.repoProject.getProjectPath(path);

        outdata,err = self.execGitCmd(cwd, cmd);

        if not outdata:
            return None,isNewGitProject;
        else:
            c = re.findall(COMMITID_RE,outdata);
            if c:
                return c, isNewGitProject;
            else:
                return None;


    def getFileStatus(self,path, commit):
        cmd = ['git', 'log', "-1", "--pretty=format:", "--name-status", commit];
        cwd = self.repoProject.getProjectPath(path);
        outdata,err = self.execGitCmd(cwd, cmd);
        fslist=[];

        if not outdata:
            return [];
        else:
            lines= outdata.splitlines();
            for l in lines:
                l = l.strip();
                if l:
                    fslist.append((l[0], l[1:].strip()));
                    
        return fslist;

    def getRegionFileStatus(self,path, commit_start, commit_end):
        cmd = ['git', 'diff', "--pretty=format:", "--name-status", ("%s^..%s" % (commit_start,commit_end))];
        cwd = self.repoProject.getProjectPath(path);
        outdata,err = self.execGitCmd(cwd, cmd);
        fslist=[];

        if not outdata:
            return [];
        else:
            lines= outdata.splitlines();
            for l in lines:
                l = l.strip();
                if l:
                    fslist.append((l[0], l[1:].strip()));
                    
        return fslist;

    def getFileContent(self,path, commit,file):
        cmd = ['git', 'show', commit+":"+file];
        cwd = self.repoProject.getProjectPath(path);
        outdata,err = self.execGitCmd(cwd, cmd);

        return outdata; 

    def getPatchContent(self,path, commit):
        cmd = ['git', 'format-patch', '--stdout', commit+"^.."+commit];
        cwd = self.repoProject.getProjectPath(path);
        outdata,err = self.execGitCmd(cwd, cmd);

        return outdata; 

    def getPatchs(self,path, commit_start, commit_end, output_path):
        print "path: " + path
        print "commit_start: " + commit_start
        print "commit_end: " + commit_end
        cmd = ['git', 'format-patch', '-o',  output_path, commit_start+"^.."+commit_end];
        cwd = self.repoProject.getProjectPath(path);
        outdata,err = self.execGitCmd(cwd, cmd);

        return outdata; 


class RepoDiffBase(object):
    def __init__(self, path, xml, outpath, outfilename, start, end, bymanifest, extraoptions):
        self.basepath = os.path.expanduser(path);
        self.outpath =os.path.expanduser(outpath); 
        self.repoProject = RepoProject(xml, self.basepath);
        self.gitOperation = GitOperation(self.repoProject);
        self.projects = self.repoProject.getProjects();
        self.outfilename = outfilename;
        self.start = start;
        self.end = end;
        self.options = extraoptions;

        self.bymanifest = bymanifest;

        if not os.path.exists(self.outpath):
            os.makedirs(self.outpath);


    def getOutFilePath(self,path):
        return os.path.join(self.outpath,path);    

    def getFlatOutFilePath(self,path):
        return os.path.join(self.outpath,path.replace("/","_").replace("\\","_"));    

    def saveFile(self, basepath,name, data):
        fileName = os.path.join(basepath,name);
        filePath = os.path.dirname(fileName);
        if not os.path.exists(filePath):
            os.makedirs(filePath);
            
        newfp = open(fileName, "w+");
        newfp.write(data);
        newfp.close();

    def process(self):
        if self.bymanifest:
            startPorjects = RepoProject(self.start, self.basepath).getProjects();
            endProjects = RepoProject(self.end, self.basepath).getProjects();
        
        self.onProcessStart();
        for p in self.projects:
        #for p in [["platform/system/vold","system/vold",""]]:
            path = p[1];

            if not os.path.exists(os.path.join(self.basepath, path)):
                print "path not exists for "+path
                continue;

            if self.bymanifest:
                startrev = endrev = "";
                #find start rev
                for sp in startPorjects:
                    if sp[1] == path :
                        startrev = sp[2];
                        break;

                #find end rev
                for ep in endProjects:
                    if ep[1] == path:
                        endrev = ep[2];
                        break;

                commits, isNew = self.gitOperation.getCommitsByRev(path, startrev, endrev);
            else:
                commits, isNew = self.gitOperation.getCommitsByTag(path, self.start, self.end);

            if not commits:
                #print "no commits found for "+path
                continue;
            self.doProcess(path, commits, isNew);
        self.onProcessEnd();
            
    def onProcessStart(self):
        print "Not implemented!";
        pass

    def onProcessEnd(self):
        print "Not implemented!";
        pass

    def doProcess(self, path, commits, isnew):
        print "Not implemented!";
        pass
    

class RepoDiff(RepoDiffBase):
    def __init__(self, path, xml, outpath, outfilename, start, end, bymanifest, extraoptions):
        super(RepoDiff, self).__init__(path, xml, outpath, outfilename, start, end, bymanifest, extraoptions);

        try:
            self.logonly = self.options["logonly"];
        except Exception,e:
            self.logonly = False;

    def getCsvOutFileName(self):
        return os.path.join(self.outpath,self.outfilename);

    def getCommitOutFilePath(self,path,commit,date):
        return os.path.join(self.getFlatOutFilePath(path),time.strftime("%Y-%m-%d %X",time.localtime(string.atol(date))).replace(" ","_").replace(":","_")+"_"+commit[-5:]);

    def onProcessStart(self):
        #open csv file   
        csv_filename = self.getCsvOutFileName();
        self.csv_fp = open(csv_filename, "w+");
        self.csv_fp.write("Path,Commit,Date,Subject,Author,Merge,New\n");

    def onProcessEnd(self):
        if self.csv_fp:
            self.csv_fp.close();

    def doProcess(self, path, commits, isnew):
        for c in commits:
            isMerge = True;

            #get diff file content
            filestatus = self.gitOperation.getFileStatus(path, c[0]);
            if filestatus:
                if self.logonly:
                    for fs in filestatus:
                        if fs[0] == 'M':
                            isMerge = False;
                        elif fs[0] == 'C':
                            pass
                        elif fs[0] == 'R':
                            pass
                        elif fs[0] == 'A':
                            isMerge = False;
                        elif fs[0] == 'D':
                            isMerge = False;
                        else:
                            pass;
                else:
                    outpath = self.getCommitOutFilePath(path,c[0],c[1]);
                    oldpath = os.path.join(outpath,"old");
                    newpath = os.path.join(outpath,"new");

                    for fs in filestatus:
                        newfiledata="";
                        oldfiledata="";

                        if fs[0] == 'M':
                            #modify
                            newfiledata = self.gitOperation.getFileContent(path, c[0], fs[1]);
                            oldfiledata = self.gitOperation.getFileContent(path, c[0]+"^", fs[1]);
                        elif fs[0] == 'C':
                            print "C: path="+path+ " file="+fs[1]+" commit="+c[0]
                        elif fs[0] == 'R':
                            print "R: path="+path+ " file="+fs[1]+" commit="+c[0]
                        elif fs[0] == 'A':
                            #print "get file:"+fs[1] +" for "+c[0]
                            newfiledata = self.gitOperation.getFileContent(path, c[0], fs[1]);
                            #print "end of get file:"+fs[1];

                        elif fs[0] == 'D':
                            #print "get file:"+fs[1] +" for "+c[0]
                            oldfiledata = self.gitOperation.getFileContent(path, c[0]+"^", fs[1]);
                            #print "end of get file:"+fs[1];

                        else:
                            pass;

                        self.saveFile(outpath,"commit_info.txt","commit: "+c[0]+"\ndate: "+ time.strftime("%Y-%m-%d %X",time.localtime(string.atol(c[1]))) +"\nsubject: "+c[2]+"\nauthor: "+c[3]+"\n")
                        if newfiledata:
                            isMerge = False;
                            self.saveFile(newpath,fs[1],newfiledata);
                        if oldfiledata:
                            isMerge = False;
                            self.saveFile(oldpath,fs[1],oldfiledata);
            else:
                pass;


            #save commit log
            loginfo = c[2].replace("\"","@");
            author = c[3].replace("\"","@");
            try:
                loginfo = loginfo.encode("gb2312", "ignore")
            except Exception,e:
                try:
                    loginfo = loginfo.decode("ISO-8859-1","ignore").encode("gb2312", "ignore")
                except Exception,e:
                    loginfo = "??????????????????"

            try:
                author = author.encode("gb2312", "ignore")
            except Exception,e:
                try:
                    author = author.decode("ISO-8859-1","ignore").encode("gb2312", "ignore")
                except Exception,e:
                    author = "??????"
            try:
                self.csv_fp.write(path+","+c[0]+",\""+time.strftime("%Y-%m-%d %X",time.localtime(string.atol(c[1])))+"\",\""+loginfo+"\""+",\""+author+"\"");
            except Exception,e:
                self.csv_fp.write(path+","+c[0]+",\""+time.strftime("%Y-%m-%d %X",time.localtime(string.atol(c[1])))+"\",\""+"??????????????????"+"\""+",\""+"??????"+"\"");
            

            if isMerge:
                self.csv_fp.write(",Yes");
            else:
                self.csv_fp.write(",No");

            if isnew:
                self.csv_fp.write(",Yes\n");
            else:
                self.csv_fp.write(",No\n");

class RepoPatch(RepoDiffBase):
    def __init__(self, path, xml, outpath, outfilename, start, end, bymanifest, extraoptions):
        super(RepoPatch, self).__init__(path, xml, outpath, outfilename, start, end, bymanifest, extraoptions);

    def getPatchOutFilePath(self,path):
        return os.path.join(self.getFlatOutFilePath(path),"patches");    

    def onProcessStart(self):
        self.changedPaths = "";
        
    def onProcessEnd(self):
        self.saveFile(self.outpath,"changed_paths.txt", self.changedPaths);

    def doProcess(self, path, commits, isnew):

        patchpath = self.getPatchOutFilePath(path);
        if not os.path.exists(patchpath):
            os.makedirs(patchpath);

        out = self.gitOperation.getPatchs(path, commits[-1][0], commits[0][0], patchpath)
         
        print "out: " + out;
        
        if not out:
            os.rmdir(patchpath);
            os.rmdir(self.getGitOutFilePath(path))
        else:
             self.changedPaths += path+"\n"; 


class RepoPatchTree(RepoDiffBase):
    def __init__(self, path, xml, outpath, outfilename, start, end, bymanifest, extraoptions):
        super(RepoPatchTree, self).__init__(path, xml, outpath, outfilename, start, end, bymanifest, extraoptions);

        try:
            self.logonly = self.options["logonly"];
        except Exception,e:
            self.logonly = False;

    def onProcessStart(self):
        self.changedFiles = "";
        
    def onProcessEnd(self):
        self.saveFile(self.outpath,"changed_files.txt", self.changedFiles);

    def doProcess(self, path, commits, isnew):
        filestatus = self.gitOperation.getRegionFileStatus(path, commits[-1][0], commits[0][0])

        if not filestatus:
            return;

        if self.logonly:
            for fs in filestatus:
                if fs[0] == 'M':
                    isMerge = False;
                elif fs[0] == 'C':
                    pass
                elif fs[0] == 'R':
                    pass
                elif fs[0] == 'A':
                    isMerge = False;
                elif fs[0] == 'D':
                    isMerge = False;
                else:
                    pass;
        else:
            outpath = self.getOutFilePath(path);

            for fs in filestatus:
                filedata="";

                if fs[0] == 'M':
                    #modify
                    filedata = self.gitOperation.getFileContent(path, commits[0][0], fs[1]);
                elif fs[0] == 'C':
                    print "C: path="+path+ " file="+fs[1]+" commit="+c[0]
                elif fs[0] == 'R':
                    print "R: path="+path+ " file="+fs[1]+" commit="+c[0]
                elif fs[0] == 'A':
                    filedata = self.gitOperation.getFileContent(path, commits[0][0], fs[1]);

                elif fs[0] == 'D':
                    filedata = "REMOVED";

                else:
                    pass;

                if filedata:
                    self.saveFile(outpath,fs[1],filedata);
       
                self.changedFiles += fs[0]+ "\t\t" + os.path.join(path,fs[1]) + "\n"; 
                    

if __name__ == "__main__":
    usage = "usage:%prog [options] starttag endtag\n%prog [options] -x startxml endxml"
    parser = OptionParser(usage=usage)
    parser.add_option("-o", "--outpath", action="store", dest="outpath", default="./repodiff_out", help="output dir for genarated data")
    parser.add_option("-r", "--rootpath", action="store", dest="rootpath", default="./", help="root path of the repo project")
    parser.add_option("-m", "--manifestfile", action="store", dest="manifestfile", default="./.repo/manifest.xml", help="manifest file of the repo project")
    parser.add_option("-e", "--relxmlpath", action="store", dest="relxmlpath", default=".repo/manifests", help="the manifest path relative to root path")
    parser.add_option("-l", action="store_true", dest="logonly", default=False, help="only grep the log")
    parser.add_option("-x", action="store_true", dest="bymanifest", default=False, help="grep diff between two manifest file")
    parser.add_option("-f", "--outfilename", action="store", dest="outfilename", default="diff_log.csv", help="output filename for genarated data")
    parser.add_option("-g", "--genpatch", action="store_true", dest="genpatch", default=False, help="genarate patchs")
    parser.add_option("-p", "--gencustompatch", action="store_true", dest="gencustompatch", default=False, help="genarate patch for custom")

    (options, args) = parser.parse_args();
    print args

    if len(args) != 2:
        print "should input two arguments"
        parser.print_help();
        sys.exit(1);

    
    outpath = options.outpath;
    rootpath = options.rootpath;
    manifestfile = options.manifestfile;
    logonly = options.logonly;
    bymanifest = options.bymanifest;
    relxmlpath = options.relxmlpath;
    outfilename = options.outfilename;

    genpatch = options.genpatch;
    gencustompatch = options.gencustompatch;

    print "gencustompatch=%s" % gencustompatch

    outpath = os.path.expanduser(outpath);
    outpath = os.path.abspath(outpath);

    rootpath = os.path.expanduser(rootpath);
    rootpath = os.path.abspath(rootpath);

    manifestfile = os.path.join(rootpath,manifestfile);
    manifestfile = os.path.expanduser(manifestfile);
    manifestfile = os.path.abspath(manifestfile);
    
    print "Android Path: "+rootpath
    print "Manifest Path: "+manifestfile
    print "Output Path: "+outpath

    if os.path.exists(outpath) and os.listdir(outpath):
        while True:
            s = raw_input("OutputPath(%s) is not empty.\nAre you sure to Delete it?(Y/N)"%outpath);
            choice = s[0].upper()
            if choice[0] in ["Y","N"]:
                if choice[0] == "Y":
                    print "Deleting......"
                    shutil.rmtree(outpath);
                    print "Delete successfully!"
                else:
                    print "%s is not empty, exit!"% outpath
                    sys.exit(1);
                break;
            else:
                print 'Error Input, Again!'
        
    if os.path.exists(rootpath) and os.path.isfile(manifestfile):
        if bymanifest: 
            startarg = os.path.join(rootpath,relxmlpath,args[0]);
            endarg = os.path.join(rootpath,relxmlpath,args[1])
            print startarg
            print endarg
            if not os.path.exists(startarg) or not os.path.exists(endarg):
                print "xml is not exist"
                parser.print_help();
                sys.exit(1)
        else:
            startarg = args[0];
            endarg = args[1];

        if genpatch:
            RepoPatch(rootpath, manifestfile, outpath, outfilename,startarg, endarg, bymanifest, {}).process();
        elif gencustompatch:
            RepoPatchTree(rootpath, manifestfile, outpath, outfilename,startarg, endarg, bymanifest, {"logonly":logonly}).process();
        else: 
            RepoDiff(rootpath, manifestfile, outpath, outfilename,startarg, endarg, bymanifest, {"logonly":logonly}).process();

    else:
        print "%s or %s is not exist" %(rootpath, manifestfile)
        parser.print_help();

        










        




    
