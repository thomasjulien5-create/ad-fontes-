#!/usr/bin/perl
# ============================================================
#  Ad Fontes — interrogation de Divinum Officium pour une date
# ------------------------------------------------------------
#  Le site divinumofficium.com est protégé contre les requêtes
#  automatiques ; on exécute donc son propre programme (missa.pl),
#  tiré de son dépôt public, avec ses données : même calendrier,
#  mêmes règles de préséance (rubriques de 1960), mêmes textes.
#
#  Ce fichier est copié par generer-jours.py dans le dossier
#  web/cgi-bin/missa du dépôt Divinum Officium (missa.pl retrouve
#  ses modules et ses données à partir de son propre dossier).
#
#  Entrée : QUERY_STRING (date1=MM-JJ-AAAA&version=…&command=praySancta Missa)
#  Sortie : un objet JSON sur la sortie standard —
#    jour du calendrier retenu, rang, couleur, commémoraisons,
#    noms latins et français, et la page de la messe (HTML).
# ============================================================
use utf8;
use strict;
no strict 'vars';
use JSON::PP;
use Encode qw(decode);

my $page = '';
{
  local *STDOUT;
  open(STDOUT, '>:utf8', \$page) or die "sortie : $!";
  do './missa.pl';
  die "missa.pl : $@" if $@;
}
$page = decode('UTF-8', $page);

# [Officium] (ou, à défaut, le premier champ de [Rank]) d'un fichier, dans une langue.
sub nom_office {
  my ($langue, $fichier) = @_;
  return '' unless $fichier;
  my $h = eval { setupstring($langue, $fichier) } || {};
  my $o = $h->{Officium} // '';
  if ($o eq '' && defined $h->{Rank}) { ($o) = split /;;/, $h->{Rank}; }
  $o //= '';
  $o =~ s/^\s+|\s+$//g;
  return $o;
}

my $tete = eval { setheadline() } // '';
my ($titre) = split / ~ /, $tete;
$titre //= '';
$titre =~ s/\s+$//;

my @comm = map { { fichier => $_, latin => nom_office('Latin', $_), francais => nom_office('Francais', $_) } } @main::commemoentries;

my $sortie = {
  gagnant          => $main::winner // '',
  scriptura        => $main::scriptura // '',
  rang             => $main::rank // '',
  entete           => $tete,
  titre_latin      => $titre,
  office_latin     => nom_office('Latin', $main::winner),
  office_francais  => nom_office('Francais', $main::winner),
  couleur          => DivinumOfficium::Main::liturgical_color($titre),
  temporal         => $main::dayname[0] // '',
  commemoraisons   => \@comm,
  html             => $page,
};

binmode STDOUT, ':raw';
print JSON::PP->new->utf8->canonical->encode($sortie);
