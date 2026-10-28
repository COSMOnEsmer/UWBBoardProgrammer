// Repository-local first-run launcher. Requires only Windows' .NET Framework.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.Serialization;
using System.Runtime.Serialization.Json;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

[DataContract] public class PackageFile {
    [DataMember(Name="path")] public string Path;
    [DataMember(Name="sha256")] public string Sha256;
    [DataMember(Name="bytes")] public long Bytes;
}
[DataContract] public class PackageManifest {
    [DataMember(Name="schema")] public int Schema;
    [DataMember(Name="version")] public string Version;
    [DataMember(Name="archive")] public string Archive;
    [DataMember(Name="archive_root")] public string ArchiveRoot;
    [DataMember(Name="sha256")] public string Sha256;
    [DataMember(Name="bytes")] public long Bytes;
    [DataMember(Name="executable")] public string Executable;
    [DataMember(Name="files")] public List<PackageFile> Files;
}
[DataContract] public class LaunchReport {
    [DataMember] public string Version;
    [DataMember] public string RepositoryRoot;
    [DataMember] public string ApplicationRoot;
    [DataMember] public string Executable;
    [DataMember] public string PayloadSha256;
    [DataMember] public bool ReusedInstallation;
    [DataMember] public int VerifiedFiles;
    [DataMember] public string Shortcut;
    [DataMember] public int? ApplicationExitCode;
}

public static class Bootstrap {
    static string Inside(string parent, string relative) {
        if (String.IsNullOrWhiteSpace(relative) || System.IO.Path.IsPathRooted(relative))
            throw new InvalidDataException("Invalid package path.");
        if (relative.IndexOf(':')>=0 || relative.Split('/','\\').Any(p=>p==".." || p=="."))
            throw new InvalidDataException("Invalid package path component.");
        string boundary=System.IO.Path.GetFullPath(parent).TrimEnd('\\','/')+System.IO.Path.DirectorySeparatorChar;
        string result=System.IO.Path.GetFullPath(System.IO.Path.Combine(parent,relative.Replace('/',System.IO.Path.DirectorySeparatorChar)));
        if (!result.StartsWith(boundary,StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Package path escapes its folder.");
        return result;
    }
    static string Hash(string path) {
        using (SHA256 sha=SHA256.Create()) using (FileStream stream=File.OpenRead(path))
            return BitConverter.ToString(sha.ComputeHash(stream)).Replace("-","").ToLowerInvariant();
    }
    static bool ValidHash(string text) {
        return text!=null && text.Length==64 && text.All(c=>"0123456789abcdef".Contains(Char.ToLowerInvariant(c)));
    }
    static void WriteJson<T>(string path,T value) {
        Directory.CreateDirectory(System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(path)));
        using(FileStream stream=new FileStream(path,FileMode.CreateNew,FileAccess.Write))
            new DataContractJsonSerializer(typeof(T)).WriteObject(stream,value);
    }
    static bool VerifyFiles(string folder,PackageManifest manifest) {
        if (!Directory.Exists(folder)) return false;
        try {
            foreach (PackageFile file in manifest.Files) {
                string path=Inside(folder,file.Path);
                if (!File.Exists(path) || new FileInfo(path).Length!=file.Bytes || Hash(path)!=file.Sha256.ToLowerInvariant()) return false;
            }
            return File.Exists(Inside(folder,manifest.Executable));
        } catch(IOException) { return false; }
        catch(UnauthorizedAccessException) { return false; }
    }
    static void CopySettings(string repository,string destination) {
        // Copy only append-only profiles/preferences; never recordings or credentials.
        foreach(string relative in new [] { "config/profiles", "data/ui-settings" }) {
            string source=Inside(repository,relative);
            if (!Directory.Exists(source)) continue;
            foreach(string file in Directory.GetFiles(source,"*.json",SearchOption.TopDirectoryOnly)) {
                if ((File.GetAttributes(file)&FileAttributes.ReparsePoint)!=0) continue;
                string target=System.IO.Path.Combine(Inside(destination,relative),System.IO.Path.GetFileName(file));
                Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));
                if (!File.Exists(target)) File.Copy(file,target,false);
            }
        }
    }
    static LaunchReport Prepare(string repository,bool verifyOnly,Action<string> progress) {
        repository=System.IO.Path.GetFullPath(repository);
        string manifestPath=Inside(repository,"deployment/windows-x64/distribution.v1.json");
        PackageManifest manifest;
        using(FileStream stream=File.OpenRead(manifestPath))
            manifest=(PackageManifest)new DataContractJsonSerializer(typeof(PackageManifest)).ReadObject(stream);
        if (manifest.Schema!=1 || !ValidHash(manifest.Sha256) || manifest.Bytes<1 ||
            manifest.Files==null || manifest.Files.Count==0 || String.IsNullOrEmpty(manifest.Version) ||
            manifest.Version.Any(c=>!"0123456789.-abcdefghijklmnopqrstuvwxyz".Contains(Char.ToLowerInvariant(c))))
            throw new InvalidDataException("Invalid distribution manifest.");
        var paths=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach(PackageFile file in manifest.Files) {
            Inside(repository,file.Path);
            if (!ValidHash(file.Sha256) || file.Bytes<0 || !paths.Add(file.Path.Replace('\\','/')))
                throw new InvalidDataException("Invalid package file manifest.");
        }
        if (!paths.Contains(manifest.Executable) || String.IsNullOrEmpty(manifest.ArchiveRoot) ||
            manifest.ArchiveRoot.IndexOfAny(new [] {'/','\\',':'})>=0)
            throw new InvalidDataException("Invalid application entry point.");
        string archive=Inside(repository,manifest.Archive);
        progress("Checking application files...");
        if (!File.Exists(archive) || new FileInfo(archive).Length!=manifest.Bytes || Hash(archive)!=manifest.Sha256.ToLowerInvariant())
            throw new InvalidDataException("The application ZIP is missing or changed. Complete git pull, then try again.");
        var result=new LaunchReport { Version=manifest.Version,RepositoryRoot=repository,PayloadSha256=manifest.Sha256,VerifiedFiles=manifest.Files.Count };
        if (verifyOnly) return result;
        // Keep the executable path short even when a clone is deep in OneDrive.
        // The repository hash isolates settings between independent checkouts.
        string repositoryKey;
        using(SHA256 sha=SHA256.Create()) repositoryKey=BitConverter.ToString(sha.ComputeHash(Encoding.UTF8.GetBytes(repository.ToLowerInvariant()))).Replace("-","").Substring(0,16).ToLowerInvariant();
        string cache=System.IO.Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"UWBBoardProgrammer","Git",repositoryKey);
        Directory.CreateDirectory(cache);
        string key="uwb-"+manifest.Version+"-"+manifest.Sha256.Substring(0,12);
        string installation=System.IO.Path.Combine(cache,key);
        string ready=Inside(installation,manifest.ArchiveRoot);
        if (!VerifyFiles(ready,manifest)) {
            // Preserve a damaged or earlier installation; repair into a new directory.
            if (Directory.Exists(installation)) {
                foreach(string candidate in Directory.GetDirectories(cache,key+"-repair-*")) {
                    if (VerifyFiles(Inside(candidate,manifest.ArchiveRoot),manifest)) {
                        installation=candidate;ready=Inside(candidate,manifest.ArchiveRoot);break;
                    }
                }
            }
        }
        if (VerifyFiles(ready,manifest)) result.ReusedInstallation=true;
        else {
            progress("Preparing UWB Board Programmer...");
            string staging=System.IO.Path.Combine(cache,".preparing-"+Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(staging);
            using(ZipArchive zip=ZipFile.OpenRead(archive)) {
                foreach(ZipArchiveEntry entry in zip.Entries) {
                    string path=Inside(staging,entry.FullName);
                    if(entry.FullName.EndsWith("/")) { Directory.CreateDirectory(path);continue; }
                    string prefix=manifest.ArchiveRoot+"/";
                    if(!entry.FullName.StartsWith(prefix,StringComparison.Ordinal) || !paths.Contains(entry.FullName.Substring(prefix.Length)))
                        throw new InvalidDataException("Unexpected file in application ZIP.");
                    Directory.CreateDirectory(System.IO.Path.GetDirectoryName(path));
                    using(Stream source=entry.Open()) using(FileStream target=new FileStream(path,FileMode.CreateNew,FileAccess.Write)) source.CopyTo(target);
                }
            }
            string prepared=Inside(staging,manifest.ArchiveRoot);
            if (!VerifyFiles(prepared,manifest)) throw new InvalidDataException("Extracted application verification failed.");
            CopySettings(repository,prepared);
            if (Directory.Exists(installation)) installation=System.IO.Path.Combine(cache,key+"-repair-"+Guid.NewGuid().ToString("N"));
            Directory.Move(staging,installation);ready=Inside(installation,manifest.ArchiveRoot);
        }
        result.ApplicationRoot=ready;result.Executable=Inside(ready,manifest.Executable);
        return result;
    }
    static string Shortcut(string repository,string executable) {
        string desktop=Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
        string path=System.IO.Path.Combine(desktop,"UWB Board Programmer - GitHub.lnk");
        Type type=Type.GetTypeFromProgID("WScript.Shell");
        dynamic shell=Activator.CreateInstance(type);
        string arguments="--root "+Quote(repository);
        if (File.Exists(path)) {
            dynamic existing=shell.CreateShortcut(path);
            if (String.Equals((string)existing.TargetPath,executable,StringComparison.OrdinalIgnoreCase) && (string)existing.Arguments==arguments) return path;
            path=System.IO.Path.Combine(desktop,"UWB Board Programmer - GitHub ("+Guid.NewGuid().ToString("N").Substring(0,8)+").lnk");
        }
        dynamic link=shell.CreateShortcut(path);
        link.TargetPath=executable;link.Arguments=arguments;link.WorkingDirectory=repository;
        link.IconLocation=executable+",0";link.Description="UWB Board Programmer: complete GitHub package, Standalone BLE and USB.";
        link.Save();return path;
    }
    static string Quote(string value) {
        if (value.Contains("\"")) throw new ArgumentException("Unexpected quote in path.");
        int trailing=value.Length-value.TrimEnd('\\').Length;
        return "\""+value+new string('\\',trailing)+"\"";
    }
    [STAThread] public static int Main(string[] args) {
        string root=System.IO.Path.GetFullPath(System.IO.Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..",".."));
        string reportPath=null,smokePath=null;bool verifyOnly=false,prepareOnly=false,noShortcut=false;
        Form splash=null;Label label=null;
        try {
            for(int i=0;i<args.Length;i++) {
                if(args[i]=="--root" && i+1<args.Length) root=System.IO.Path.GetFullPath(args[++i]);
                else if(args[i]=="--report" && i+1<args.Length) reportPath=System.IO.Path.GetFullPath(args[++i]);
                else if(args[i]=="--smoke-output" && i+1<args.Length) smokePath=System.IO.Path.GetFullPath(args[++i]);
                else if(args[i]=="--verify-only") verifyOnly=true;
                else if(args[i]=="--prepare-only") prepareOnly=true;
                else if(args[i]=="--no-shortcut") noShortcut=true;
                else throw new ArgumentException("Unknown launcher option: "+args[i]);
            }
            if(!Environment.Is64BitOperatingSystem || Environment.OSVersion.Platform!=PlatformID.Win32NT || Environment.OSVersion.Version.Major<10)
                throw new PlatformNotSupportedException("Windows 10/11 64-bit is required.");
            bool interactive=!verifyOnly && !prepareOnly && smokePath==null;
            if(interactive) {
                Application.EnableVisualStyles();
                splash=new Form { Text="UWB Board Programmer",Width=470,Height=150,StartPosition=FormStartPosition.CenterScreen,
                                  FormBorderStyle=FormBorderStyle.FixedDialog,MaximizeBox=false,MinimizeBox=false,ControlBox=false };
                label=new Label { Left=22,Top=22,Width=420,Height=32,Text="Preparing application..." };
                splash.Controls.Add(label);splash.Controls.Add(new ProgressBar { Left=22,Top=64,Width=420,Height=16,Style=ProgressBarStyle.Marquee });
                splash.Show();splash.Refresh();
            }
            LaunchReport result=Prepare(root,verifyOnly,delegate(string text) { if(label!=null) { label.Text=text;Application.DoEvents(); } });
            if(!verifyOnly && !noShortcut) result.Shortcut=Shortcut(root,Assembly.GetExecutingAssembly().Location);
            if(!verifyOnly && !prepareOnly) {
                string arguments="--workspace "+Quote(result.ApplicationRoot);
                if(smokePath!=null) arguments+=" --smoke-output "+Quote(smokePath);
                var start=new ProcessStartInfo(result.Executable,arguments) { WorkingDirectory=result.ApplicationRoot,UseShellExecute=false };
                start.EnvironmentVariables.Remove("PYTHONHOME");start.EnvironmentVariables.Remove("PYTHONPATH");
                start.EnvironmentVariables.Remove("QT_PLUGIN_PATH");start.EnvironmentVariables.Remove("QT_QPA_PLATFORM_PLUGIN_PATH");
                using(Process process=Process.Start(start)) {
                    if(smokePath!=null) {
                        if(!process.WaitForExit(60000)) throw new TimeoutException("Application smoke check timed out.");
                        result.ApplicationExitCode=process.ExitCode;
                        if(process.ExitCode!=0) throw new InvalidOperationException("Application exited with code "+process.ExitCode);
                    }
                }
            }
            if(reportPath!=null) WriteJson(reportPath,result);
            Console.WriteLine("UWB Board Programmer "+result.Version+" ready.");
            return 0;
        } catch(Exception error) {
            Console.Error.WriteLine(error.Message);
            if(!verifyOnly && !prepareOnly && smokePath==null)
                MessageBox.Show("Could not open UWB Board Programmer.\r\n\r\n"+error.Message,"UWB Board Programmer",MessageBoxButtons.OK,MessageBoxIcon.Error);
            return 1;
        } finally { if(splash!=null) splash.Close(); }
    }
}
