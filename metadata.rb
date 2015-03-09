name             'AWS_see_spots_run'
maintainer       "Brandon O'Connor"
maintainer_email 'brandoconnor@gmail.com'
license          'Apache 2.0'
description      'Installs/Configures AWS_see_spots_run, a spot instance management platform.'
long_description IO.read(File.join(File.dirname(__FILE__), 'README.md'))
#source_url       'https://github.com/dreamboxlearning/AWS_see_spots_run'
#issues_url       'https://github.com/dreamboxlearning/AWS_see_spots_run/issues'
version          '0.1.5'
depends          'python'

%w[
  ubuntu
  debian
  centos
  redhat
  fedora
  amazon
].each do |os|
  supports os
end
