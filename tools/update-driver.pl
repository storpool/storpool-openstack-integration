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

my $debug = 0;

sub debug($);
sub usage($);
sub version();

sub scan_template_file($ $);
sub update_file($ $ $);
sub copy_file($ $);
sub mkdir_p_basedir($ $);
sub mkdir_p_rec($ $);

my %data = (
	'cinder/brick/initiator/connector.py' => [
		{
			type => 'chunk',
			from => qr/^\s+elif protocol == "STORPOOL"/,
			to => qr/^\s+elif protocol == "LOCAL"/,
		},
		{
			type => 'class',
			name => 'StorPoolConnector',
		},
	],
	'cinder/exception.py' => [
		{
			type => 'class',
			name => 'StorPoolConfigurationMissing',
		},
		{
			type => 'class',
			name => 'StorPoolConfigurationInvalid',
		},
	],
	'cinder/volume/drivers/storpool.py' => [
		{
			type => 'new',
		},
	],

	'nova/virt/libvirt/driver.py' => [
		{
			type => 'chunk',
			from => qr/^\s+'storpool=nova\./,
			to => qr/^\s+'iser=nova\./,
		},
	],
	'nova/virt/libvirt/volume.py' => [
		{
			type => 'class',
			name => 'LibvirtStorPoolVolumeDriver',
		},
	],
);

MAIN:
{
	my %cfg = (
		templdir	=> undef,
		srcdir		=> undef,
		dstdir		=> undef,
	);
	my %opts;

	getopts('f:hLt:Vv', \%opts) or usage 1;
	version() if $opts{V};
	usage 0 if $opts{h};
	exit 0 if $opts{V} || $opts{h};
	$debug = $opts{v};

	if (!defined $opts{f}) {
		warn "No driver flavor (-f) specified!\n";
		usage 1;
	} elsif ($opts{f} !~ /^(cinder|nova)$/) {
		warn "Unrecognized driver flavor '$opts{f}'\n";
		usage 1;
	} else {
		$cfg{flavor} = $opts{f};
	}

	if (defined $opts{L}) {
		while (my ($fname, $d) = each %data) {
			if ($fname !~ m{^([^/]+)/(.+)}) {
				die "Internal error: invalid data key ".
				    "'$fname'\n";
			}
			my ($flavor, $fn) = ($1, $2);
			next unless $flavor eq $cfg{flavor};
			
			say $fname.
			    (@{$d} == 1 && $d->[0]->{type} eq 'new'? '!': '');
		}
		exit 0;
	}

	if (!defined $opts{t}) {
		warn "No template directory (-t) specified!\n";
		usage 1;
	} else {
		$cfg{templdir} = $opts{t};
	}
	if (@ARGV != 2) {
		warn "No original and target directory specified\n";
		usage 1;
	}
	@cfg{qw/srcdir dstdir/} = @ARGV;

	for my $fname (sort keys %data) {
		if ($fname !~ m{^([^/]+)/(.+)}) {
			die "Internal error: invalid data key '$fname'\n";
		}
		my ($flavor, $fn) = ($1, $2);
		next unless $flavor eq $cfg{flavor};

		my $d = $data{$fname};
		if (@{$d} == 1 && $d->[0]->{type} eq 'new') {
			mkdir_p_basedir $cfg{dstdir}, $fn;
			copy_file "$cfg{templdir}/$fn", "$cfg{dstdir}/$fn";
			next;
		}
		scan_template_file "$cfg{templdir}/$fn", $d;
		mkdir_p_basedir $cfg{dstdir}, $fn;
		update_file "$cfg{srcdir}/$fn", "$cfg{dstdir}/$fn", $d;
	}
}

sub scan_template_file($ $)
{
	my ($fname, $data) = @_;

	for my $d (@{$data}) {
		if ($d->{type} eq 'chunk') {
			$d->{data} = { res => undef, done => 0 };
		} elsif ($d->{type} eq 'class') {
			$d->{data} = {
				res => undef,
				done => 0,
				from => qr/^class\s+\Q$d->{name}\E\s*[(]/,
			};
			debug "whee d->{data}->{from} is $d->{data}->{from}";
		} else {
			die "Internal error: invalid data type $d->{type}\n";
		}
	}

	open my $f, '<', $fname or
	    die "Could not open $fname: $!\n";
	while (<$f>) {
		my $in = 0;
		for my $d (@{$data}) {
			if ($d->{type} eq 'chunk') {
				if ($d->{data}->{done}) {
					if ($_ =~ $d->{from}) {
						die "Duplicate match for '$d->{from}' in $fname\n";
					}
				} elsif (!defined $d->{data}->{res}) {
					if ($_ =~ $d->{from}) {
						$d->{data}->{res} = $_;
						$in++;
					}
				} else {
					$in++;
					if ($_ =~ $d->{to}) {
						$d->{data}->{done} = 1;
					} else {
						$d->{data}->{res} .= $_;
					}
				}
			} elsif ($d->{type} eq 'class') {
				if ($d->{data}->{done}) {
					if ($_ =~ $d->{data}->{from}) {
						die "Duplicate match for class '$d->{name}' in $fname\n";
					}
				} elsif (!defined $d->{data}->{res}) {
					if ($_ =~ $d->{data}->{from}) {
						$d->{data}->{res} = $_;
						$in++;
					}
				} else {
					$in++;
					if ($_ eq "\n" && $d->{data}->{res} =~ /\n\n\Z/) {
						$d->{data}->{res} =~ s/\n\Z//;
						$d->{data}->{done} = 1;
					} else {
						$d->{data}->{res} .= $_;
					}
				}
			} else {
				die "Internal error: shouldn't have reached this point with chunk type '$d->{type}'";
			}
		}
		if ($in > 1) {
			die "More than one match for line $. in $fname\n";
		}
	}
	close $f or
	    die "Could not close $fname: $!\n";

	for my $d (@{$data}) {
		next unless $d->{type} eq 'class' &&
		    defined $d->{data}->{res} &&
		    !$d->{data}->{done};
		$d->{data}->{done} = 1;
		$d->{data}->{res} =~ s/\n+\Z/\n/;
	}
}

sub update_file($ $ $)
{
	my ($srcname, $dstname, $data) = @_;

	open my $src, '<', $srcname or
	    die "Could not open $srcname: $!\n";
	open my $dst, '>', $dstname or
	    die "Could not open $dstname: $!\n";

	for my $d (@{$data}) {
		if (!defined $d->{data}->{res}) {
			die "Internal error: found an ungathered piece of $d->{type} from the template of $srcname\n";
		}

		$d->{data}->{in} = $d->{data}->{done} = 0;

		if ($d->{type} eq 'chunk') {
			;
		} elsif ($d->{type} eq 'class') {
			if (!defined $d->{data}->{from}) {
				die "Internal error: found an unprocessed class $d->{name} from the template of $srcname\n";
			}
		} else {
			die "Internal error: invalid data type $d->{type}\n";
		}
	}

	my $last = "";
	while (<$src>) {
		my ($copy, $in) = (1, 0);

		for my $d (@{$data}) {
			if ($d->{type} eq 'chunk') {
				if ($d->{data}->{done}) {
					if ($_ =~ $d->{from}) {
						die "Duplicate match for '$d->{from}' in $srcname\n";
					}
				} elsif (!$d->{data}->{in}) {
					if ($_ =~ $d->{from}) {
						$d->{data}->{in} = 1;
						$copy = 0;
						$in++;
					} elsif ($_ =~ $d->{to}) {
						$d->{data}->{done} = 1;
						print $dst $d->{data}->{res};
					}
				} else {
					if ($_ =~ $d->{to}) {
						$d->{data}->{in} = 0;
						$d->{data}->{done} = 1;
						print $dst $d->{data}->{res};
					} else {
						$copy = 0;
						$in++;
					}
				}
			} elsif ($d->{type} eq 'class') {
				if ($d->{data}->{done}) {
					if ($_ =~ $d->{data}->{from}) {
						die "Duplicate match for class '$d->{name}' in $srcname\n";
					}
				} elsif (!$d->{data}->{in}) {
					if ($_ =~ $d->{data}->{from}) {
						debug "Found class $d->{name} in $srcname";
						$d->{data}->{in} = 1;
						$copy = 0;
						$in++;
					}
				} else {
					if ($_ eq "\n" && $last eq "\n") {
						debug "Outputting class $d->{name} to $dstname";
						$d->{data}->{in} = 0;
						$d->{data}->{done} = 1;
						print $dst "$d->{data}->{res}\n\n";
					}
					$copy = 0;
					$in++;
				}
			}
		}

		if ($in > 1) {
			die "Multiple matches for line $. in $srcname\n";
		}
		if ($copy) {
			print $dst $_;
		}
		$last = $_;
	}

	# Append the unmatched classes to the end of the file
	for my $d (@{$data}) {
		next if $d->{data}->{done};

		if ($d->{type} eq 'chunk') {
			die "Unmatched chunk in $srcname:\n$d->{data}->{res}\n";
		} elsif ($d->{type} eq 'class') {
			debug "About to add class $d->{name} to the end of $dstname\n";
			print $dst "\n\n$d->{data}->{res}";
		}
	}

	close $dst or
	    die "Could not close $dstname: $!\n";
	close $src or
	    die "Could not close $srcname: $!\n";
}

sub usage($)
{
	my ($err) = @_;
	my $s = <<EOUSAGE
Usage:	update-driver [-v] -t templatedir -f flavor origdir storpooldir
	update-driver -L -f flavor
	update-driver -V | -h

	-f	specify the driver type to update ('cinder' or 'nova')
	-h	display program usage information and exit
	-L	list the files for the specified flavor
	-t	specify the directory to extract the StorPool driver template
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
	print "update-driver 0.1.0.dev1520\n";
}

sub debug($)
{
	print STDERR "RDBG $_[0]\n" if $debug;
}

sub mkdir_p_basedir($ $)
{
	my ($base, $dir) = @_;

	if (! -d $base) {
		die "The base directory $base does not exist\n";
	}
	if (!mkdir_p_rec $base, dirname $dir) {
		die "Could not create $base/$dir or its predecessors\n";
	}
	return 1;
}

sub mkdir_p_rec($ $)
{
	my ($base, $dir) = @_;
	my $new = "$base/$dir";

	debug "mkdir_p_rec base $base dir $dir";
	return 1 if -d $new;
	return 1 if mkdir $new;
	die "Could not create the directory $new: $!\n" unless $!{ENOENT};

	my $up = dirname $dir;
	debug "ufff, up $up";
	if ($up eq $dir || $up =~ /^(.|\/|)$/) {
		return 0;
	}
	return 0 unless mkdir_p_rec $base, $up;
	return 1 if mkdir $new;
	die "Could not create the directory $new: $!\n";
}

sub copy_file($ $)
{
	my ($srcname, $dstname) = @_;

	open my $src, '<', $srcname or
	    die "Could not open $srcname: $!\n";
	open my $dst, '>', $dstname or
	    die "Could not open $dstname: $!\n";
	{
		local $/;
		my $contents = <$src>;
		print $dst $contents;
	}
	close $dst or die "Could not close $dstname: $!\n";
	close $src or die "Could not close $srcname: $!\n";
}
