#!/usr/bin/perl
#
# Copyright (c) 2015  Peter Pentchev
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

use Fcntl ':mode';
use File::Basename;
use Getopt::Std;
use POSIX ':sys_wait_h';

my $verbose = 0;

sub install_mimic($ $; $);

sub run_command(@);
sub check_wait_result($ $ $);

sub usage($);
sub version();
sub debug($);

MAIN:
{
	my %opts;

	getopts('hr:Vv', \%opts) or usage 1;
	version if $opts{V};
	usage 0 if $opts{h};
	exit 0 if $opts{V} || $opts{h};
	$verbose = $opts{v};

	my $ref = $opts{r};
	if (@ARGV > 1 && -d $ARGV[-1]) {
		my $dir = pop @ARGV;

		install_mimic $_, "$dir/".basename($_), $ref for @ARGV;
	} elsif (@ARGV == 2) {
		install_mimic $ARGV[0], $ARGV[1], $ref;
	} else {
		usage 1;
	}
}

sub install_mimic($ $; $)
{
	my ($src, $dst, $ref) = @_;

	$ref //= $dst;
	my @st = stat $ref or
	    die "Could not obtain information about $ref: $!\n";
	my $res = run_command 'install', '-c', '-o', $st[4], '-g', $st[5],
	    '-m', sprintf('%04o', S_IMODE($st[2])), $src, $dst;
	debug $res;
}

sub run_command(@)
{
	my @cmd = @_;
	debug "@cmd";
	my $pid = open my $pipe, '-|';
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

sub usage($)
{
	my ($err) = @_;
	my $s = <<EOUSAGE
Usage:	install-mimic [-v] [-r reffile] srcfile dstfile
	install-mimic [-v] [-r reffile] file1 [file2...] directory
	install-mimic -V | -h

	-h	display program usage information and exit
	-V	display program version information and exit
	-r	specify a reference file to obtain the information from
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
	print "install-mimic 0.1.0\n";
}

sub debug($)
{
	return unless $verbose;

	my ($msg) = @_;
	return unless defined $msg && length $msg;
	$msg =~ s/\n*\Z//;
	say $msg;
}
