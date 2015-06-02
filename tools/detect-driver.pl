#!/usr/bin/perl
#
# Copyright (c) 2015  StorPool
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR AND CONTRIBUTORS ``AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE AUTHOR OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS
# OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF
# SUCH DAMAGE.

use v5.10;
use strict;
use warnings;

use File::Basename qw/dirname/;
use Getopt::Std;
use POSIX qw/:sys_wait_h/;

my $debug = 0;

sub get_python_dirs();
sub get_flavor_files($);
sub determine_release($);

sub run_command(@);
sub check_wait_result($ $ $);

sub debug($);
sub usage($);
sub version();

MAIN:
{
	my $dir;
	my @flavors = qw/cinder nova/;
	my %opts;

	getopts('d:hVv', \%opts) or usage 1;
	version() if $opts{V};
	usage 0 if $opts{h};
	exit 0 if $opts{V} || $opts{h};
	$debug = $opts{v};

	if (defined $opts{d}) {
		$dir = $opts{d};
	} else {
		$dir = 'build';
	}

	if (! -d $dir) {
		mkdir $dir or die "Could not create $dir: $!\n";
	}

	my @search = get_python_dirs;
	debug "Python search path: @search";

	for my $flavor (@flavors) {
		my $sysdir = "$dir/sys-$flavor";
		if (-e $sysdir) {
			if (-l $sysdir) {
				debug "Removing the $sysdir symlink";
				unlink $sysdir or
				    die "Could not remove the $sysdir ".
				    "symlink: $!\n";
			} else {
				die "$sysdir exists and it is not a symlink\n";
			}
		}

		my @files = get_flavor_files $flavor;
		debug "Got $flavor files: @files";
		# When detecting, do not look for new files
		@files = grep !/!$/, @files;
		debug "Fixed-up $flavor files: @files";

		my $pdir;
		for my $d (@search) {
			my @found = grep -f "$d/$_", @files;
			next unless @found;
			if (@found != @files) {
				# Pfth, yes, we *are* doing it again
				my @missing = grep ! -f "$d/$_", @files;

				die "Inconsistent $flavor installation: ".
				    "some files found in $d, but not all; ".
				    "found @found, missing @missing\n";
			}

			$pdir = "$d/$flavor";
			last;
		}
		if (!defined $pdir) {
			die "No $flavor Python modules installed\n";
		}
		debug "Found $flavor in $pdir";
		symlink $pdir, $sysdir;
	}

	# Okay, now try to figure out which release we're running
	my $release = determine_release $dir;
	{
		my $fname = "$dir/os-release";
		open my $f, '>', $fname or die "Could not open $fname: $!\n";
		say $f $release;
		close $f or die "Could not close $fname: $!\n";
		debug "Wrote $release to $fname";
	}

	for my $flavor (@flavors) {
		my $src = "../drivers/$flavor/openstack/$release";
		my $dst = "$dir/tpl-$flavor";

		if (-e $dst) {
			if (-l $dst) {
				unlink $dst or
				    die "Could not remove $dst: $!\n";
			} else {
				die "$dst exists and is not a symlink\n";
			}
		}
		symlink $src, $dst or
		    die "Could not create a symlink $dst to $src: $!\n";

		my $build = "$dir/build-$flavor";
		if (-e $build) {
			if (! -d $build) {
				die "$build exists and is not a directory\n";
			} else {
				opendir my $d, $build or
				    die "Could not opendir $build: $!\n";
				while (readdir $d) {
					if (!/^\.\.?$/) {
						die "The directory $build ".
						    "is not empty\n";
					}
				}
				closedir $d or
				    die "Could not closedir $build: $!\n";
			}
		} else {
			mkdir $build or
			    die "Could not create the directory $build: $!\n";
		}
	}
}

sub usage($)
{
	my ($err) = @_;
	my $s = <<EOUSAGE
Usage:	detect-driver [-v] [-d builddir]
	detect-driver -V | -h

	-d	specify the build directory (default: "./build")
	-h	display program usage information and exit
	-V	display program version information and exit
	-v	verbose operation; display diagnostic output
EOUSAGE
	;

	if ($err) {
		die $s;
	} else {
		print "$s";
	}
}

sub version()
{
	print "detect-driver 0.1.0.dev1520\n";
}

sub debug($)
{
	print STDERR "RDBG $_[0]\n" if $debug;
}

sub get_flavor_files($)
{
	my ($flavor) = @_;

	my $res = run_command 'tools/update-driver.pl', '-L', '-f', "$flavor";
	my @lines = split /\n/, $res;
	if (!@lines) {
		die "update-driver returned no files for flavor '$flavor'\n";
	}
	my @weird = grep !/^\Q$flavor\E\//, @lines;
	if (@weird) {
		die "update-driver returned weird filenames for flavor '$flavor':\n".
		    join '', map "\t$_\n", @weird;
	}
	return @lines;
}

sub run_command(@)
{
	my @cmd = @_;
	debug "About to run @cmd";
	my $pid = open(my $pipe, '-|');
	if (!defined $pid) {
		die "Could not fork for '@cmd': $!\n";
	} elsif ($pid == 0) {
		exec { $cmd[0] } @cmd;
		die "Could not run '@cmd': $!\n";
	}

	my $output;
	{
		local $/;
		$output = <$pipe>;
	}
	my $res = close $pipe;
	my $msg = $!;
	my $status = $?;
	check_wait_result $status, $pid, "@cmd";
	if (!$res) {
		die "Some error occurred closing the pipe from '@cmd': $msg\n";
	}
	return $output;
}

sub check_wait_result($ $ $)
{
	my ($stat, $pid, $name) = @_;

	if (WIFEXITED($stat)) {
		if (WEXITSTATUS($stat) != 0) {
			die "Program '$name' (pid $pid) exited with ".
			    "non-zero status ".WEXITSTATUS($stat)."\n";
		}
	} elsif (WIFSIGNALED($stat)) {
		die "Program '$name' (pid $pid) was killed by signal ".
		    WTERMSIG($stat)."\n";
	} elsif (WIFSTOPPED($stat)) {
		die "Program '$name' (pid $pid) was stopped by signal ".
		    WSTOPSIG($stat)."\n";
	} else {
		die "Program '$name' (pid $pid) neither exited nor was ".
		    "it killed or stopped; what does wait(2) status $stat ".
		    "mean?!\n";
	}
}

sub get_python_dirs()
{
	my $res = run_command 'python', '-c', 'import sys; print str.join("\n", sys.path)';
	my @lines = split "\n", $res;
	if (!@lines) {
		die "Python did not report a module search path at all\n";
	}
	@lines = grep length && -d, @lines;
	if (!@lines) {
		die "Python did not report any existing module directories\n";
	}
	return @lines;
}

sub determine_release($)
{
	my ($dir) = @_;

	my $fname = "$dir/sys-cinder/volume/driver.py";
	open my $f, '<', $fname or die "Could not open $fname: $!\n";
	my $found;
	while (<$f>) {
		if (/from oslo\.config import/) {
			return 'juno';
		} elsif (/_sparse_copy_volume_data/) {
			return 'liberty';
		} elsif (!$found && /^class BaseVD/) {
			$found = 'kilo';
		}
	}
	close $f or die "Could not close $fname: $!\n";
	return $found;
}
