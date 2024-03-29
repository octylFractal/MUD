__author__ = 'Kenzie Togami'
import templates
import datacache
import requests
import shutil
import os
exist = os.path.exists


is_dep = False
mods = 'src/mods'
if not exist(mods):
    os.makedirs(mods)


def fetch_site_and_process(mod):
    global is_dep
    site = mod.site
    template = mod.template or templates.find_template(site)
    try:
        old_version = datacache.find_version(mod)
        version, download = template.parse_site(mod, requests.get(site), mod.max_version)
        assert version, "no version for {}".format(mod)
        assert download, "no download link for {}".format(mod)
        had_old_ver = old_version is not None
        old_version = old_version if had_old_ver else '0.0.0'
        mod_with_version = mod.with_version(version)
        mod_with_max_version = mod.with_version(mod.max_version, silent_on_fail=True)
        mod_with_old_version = mod.with_version(old_version)
        # check version status
        assert mod_with_old_version <= mod_with_version, "{} should not be less than {}".format(version, old_version)
        if mod_with_old_version == mod_with_version or (mod.max_version and mod_with_version > mod_with_max_version):
            print("No upgrade for {}".format(mod))
            return
        print("Found upgrade for {} from {} to {}".format(mod, old_version, version))
        if had_old_ver:
            print("Removing old version...")
            os.remove(mods + '/' + mod_with_old_version.get_versioned_file_name())
            print("Removed.")
        # ask template to collect changes and then write them
        print('Fetching changelog...')
        changelog = template.collect_changelogs(
            mod_with_old_version, mod_with_version)
        if changelog:
            with open(mods + '/changelogs/' + mod_with_version.get_versioned_file_name(),
                      'w+') as o:
                o.write(changelog)
            print('Fetched.')
        else:
            print('No changelog.')
        print("Fetching dependencies...")
        is_dep = True
        try:
            for dep in mod.dependencies:
                fetch_site_and_process(dep)
        finally:
            is_dep = False
        print("Fetched.")
        print("Downloading update...")
        req = requests.get(download, stream=True)
        req.raise_for_status()
        chunks = 1024  # 1k chunks download
        i = req.raw
        with open(mods + '/' + mod_with_version.get_versioned_file_name(), 'wb+') as o:
            shutil.copyfileobj(i, o, chunks)
        print("Downloaded.")
        datacache.put(mod_with_version)
        if not is_dep:
            datacache.save()
    except:
        print('Failed template', type(template))
        raise
