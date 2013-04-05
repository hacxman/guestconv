# coding: utf-8
# guestconv
#
# Copyright (C) 2013 Red Hat Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

import re

from guestconv.exception import *

from guestconv.converters.base import BaseConverter

# libguestfs currently returns all exceptions as RuntimeError. We hope this
# might be improved in the future, but in the meantime we capture the intention
# with this placeholder
GuestFSException = RuntimeError

class BootLoaderNotFound(Exception): pass

def augeas_error(h, ex):
    msg = str(ex) + '\n'
    try:
        for error in h.aug_match(u'/augeas/files//error'):
            m = re.match(u'^/augeas/files(/.*)/error$', error)
            file_path = m.group(1)

            detail = {}
            for detail_path in h.aug_match(error + u'//*'):
                m = re.match(u'^%s/(.*)$' % error, detail_path)
                detail[m.group(1)] = h.aug_get(detail_path)

            msg += u'augeas error for %s' % file_path
            if u'message' in detail:
                msg += ': %s' % detail[u'message']
            msg += '\n'

            if u'pos' in detail and u'line' in detail and u'char' in detail:
                msg += u'error at line %s, char %s, file position %s\n' % \
                       (detail[u'line'], detail[u'char'], detail[u'pos'])

            if u'lens' in detail:
                msg += u'augeas lens: %s\n' % detail[u'lens']
    except GuestFSException as new:
        raise ConversionError(
                u'error generating augeas error: %s\n' % new +
                u'original error: %s' % ex)

    msg = msg.strip()

    if len(msg) > 0:
        raise ConversionError(msg)

    raise ex


# Functions supported by grubby, and therefore common between grub legacy and
# grub2
class Grub(object):
    def get_initrd(self, path):
        for line in h.command_lines([u'grubby', u'--info', path]):
            m = re.match(u'^initrd=(\S+)', line)
            if m is not None:
                return m.group(1)

        raise ConversionError(
            u"grubby didn't return an initrd for kernel %s" % path)


# Methods for inspecting and manipulating grub legacy
class GrubLegacy(Grub):
    def __init__(self, h, root, logger):
        self._h = h
        self._root = root
        self._logger = logger

        self._grub_conf = None
        for path in [u'/boot/grub/grub.conf', u'/boot/grub/menu.lst']:
            if h.exists(path):
                self._grub_conf = path
                break

        if self._grub_conf is None:
            raise BootLoaderNotFound()

        # Find the path which needs to be prepended to paths in grub.conf to
        # make them absolute
        # Look for the most specific mount point discovered
        self._grub_fs = ''
        mounts = h.inspect_get_mountpoints(root)
        for path in [u'/boot/grub', u'/boot']:
            if path in mounts:
                self._grub_fs = path
                break

        # We used to check that the augeas grub lens included our specific
        # grub.conf location, but augeas has done this by default for some time
        # now.

    def list_kernels(self):
        h = self._h
        grub_conf = self._grub_conf
        grub_fs = self._grub_fs

        # List all kernels from grub.conf in the order that grub would try them

        paths = []
        # Try to add the default kernel to the front of the list. This will
        # fail if there is no default, or if the default specifies a
        # non-existent kernel.
        try:
            default = h.aug_get(u'/files%s/default' % grub_conf)
            paths.extend(
                h.aug_match(u'/files%s/title[%s]/kernel' % (grub_conf, default))
            )
        except GuestFSException:
            pass # We don't care

        # Add kernel paths from grub.conf in the order they are listed. This
        # will add the default kernel twice, but it doesn't matter.
        try:
            paths.extend(h.aug_match(u'/files%s/title/kernel' % grub_conf))
        except GuestFSException as ex:
            augeas_error(h, ex)

        # Fetch the value of all detected kernels, and sanity check them
        kernels = []
        checked = {}
        for path in paths:
            if path in checked:
                continue
            checked[path] = True

            try:
                kernel = grub_fs + h.aug_get(path)
            except GuestFSException as ex:
                augeas_error(h, ex)

            if h.exists(kernel):
                kernels.append(kernel)
            else:
                self._logger.warn(u"grub refers to %s, which doesn't exist" %
                                  kernel)

        return kernels


class Grub2(Grub):
    def list_kernels(self):
        h = self._h

        kernels = []

        # Get the default kernel
        default = h.command([u'grubby', u'--default-kernel']).strip()
        if len(default) > 0:
            kernels.append(default)

        # This is how the grub2 config generator enumerates kernels
        for kernel in (h.glob_expand(u'/boot/kernel-*') +
                       h.glob_expand(u'/boot/vmlinuz-*') +
                       h.glob_expand(u'/vmlinuz-*')):
            if (kernel != default and
                   not re.match(u'\.(?:dpkg-.*|rpmsave|rpmnew)$', kernel)):
                kernels.append(kernel)

        return kernels


class Grub2BIOS(Grub2):
    def __init__(self, h, root, logger):
        if not h.exists(u'/boot/grub2/grub.cfg'):
            raise BootLoaderNotFound()

        self._h = h
        self._root = root
        self._logger = root


class Grub2EFI(Grub2):
    def __init__(self, h, root, logger):
        self._h = h
        self._root = root
        self._logger = logger

        self._disk = None
        # Check all devices for an EFI boot partition
        for device in h.list_devices():
            try:
                guid = h.part_get_gpt_type(device, 1)
            except GuestFSException:
                # Not EFI if partition isn't GPT
                next

            if guid == u'C12A7328-F81F-11D2-BA4B-00A0C93EC93B':
                self._disk = device
                break

        # Check we found an EFI boot partition
        if self._disk is None:
            raise BootLoaderNotFound()

        # Look for the EFI boot partition in mountpoints
        try:
            mp = h.mountpoints()[device + '1']
        except KeyError:
            logger.debug(u'Detected EFI bootloader with no mountpoint')
            raise BootLoaderNotFound()

        self._cfg = None
        for path in h.find(mp):
            if re.search(u'/grub\.cfg$', path):
                self._cfg = mp + path
                break

        if self._cfg is None:
            logger.debug(u'Detected mounted EFI bootloader but no grub.cfg')
            raise BootLoaderNotFound()


class RedHat(BaseConverter):
    def __init__(self, h, target, root, logger):
        super(RedHat,self).__init__(h, target, root, logger)
        distro = h.inspect_get_distro(root)
        if (h.inspect_get_type(root) != 'linux' or
                h.inspect_get_distro(root) not in ('rhel', 'fedora')):
            raise UnsupportedConversion

    def inspect(self):
        bootloaders = {}
        info = {}
        devices = {}

        h = self._h
        root = self._root

        info['hostname'] = h.inspect_get_hostname(root)
        info['os'] = h.inspect_get_type(root)
        info['distribution'] = h.inspect_get_distro(root)
        info['version'] = {
            'major': h.inspect_get_major_version(root),
            'minor': h.inspect_get_minor_version(root)
        }

        self._bootloader = self._inspect_bootloader()
        print self._bootloader.list_kernels()

        return bootloaders, info, devices

    def _inspect_bootloader(self):
        for bl in [GrubLegacy, Grub2BIOS, Grub2EFI]:
            try:
                return bl(self._h, self._root, self._logger)
            except BootLoaderNotFound:
                pass # Try the next one

        raise ConversionError(u'Did not detect a bootloader for root %s' %
                              self._root)

    def convert(self, bootloaders, devices):
        self._logger.info('Converting root %s' % self._root)
