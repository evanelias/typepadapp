# Copyright (c) 2010 Six Apart Ltd.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of Six Apart Ltd. nor the names of its contributors may
#   be used to endorse or promote products derived from this software without
#   specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import logging
import re
try:
    from hashlib import sha1
except ImportError:
    import sha as sha1
import hmac
try:
    import xml.etree.cElementTree as ElementTree
except ImportError:
    from elementtree import ElementTree

from django.contrib.csrf.middleware import csrf_exempt
from django.http import HttpResponse, HttpResponseForbidden
from iso8601 import iso8601
import simplejson as json

from typepadapp.models.feedsub import Subscription
from typepadapp import signals


log = logging.getLogger(__name__)
"""A `logging` logger for sharing debug and status messages."""


@csrf_exempt
def callback(request, *args, **kwargs):
    """Accept a subscription or feed from TypePad."""
    mode = request.GET.get('hub.mode', None)

    if mode is None:
        # No mode means it's feed content from TypePad.
        return receive(request, *args, **kwargs)
    elif mode == 'subscribe':
        return subscribe(request, *args, **kwargs)

    return HttpResponse('Unknown hub.mode %r' % mode, status=400, content_type='text/plain')


def receive(request, sub_id):

    payload = request.raw_post_data
    subscription = Subscription.objects.get(id=sub_id)

    # If this subscription has a secret, check for a signature.
    if subscription.secret:
        try:
            log.debug(repr(request.META))
            try:
                signature = request.META['HTTP_X_HUB_SIGNATURE']
            except KeyError:
                log.warning('Received content for subscription #%d %s with no signature', subscription.id, subscription.name)
                return HttpResponseForbidden('No signature given but signature is required', content_type='text/plain')

            # Django will give us the secret back as unicode, so make it a bytestring again.
            secret = subscription.secret.encode('utf-8')
            signer = hmac.new(secret, payload, sha1)
            expected = 'sha1=%s' % signer.hexdigest()

            log.debug('Received signature header %r and expecting %r', signature, expected)

            if signature != expected:
                return HttpResponseForbidden('Incorrect signature for this payload', content_type='text/plain')
        except Exception, exc:
            log.exception(exc)
            raise

    # TBD: change this switch to something based on content-type once
    # TypePad identifies a content-type of json versus xml
    is_atom = re.match('\s*<', payload) is not None
    is_json = not is_atom and re.match('\s*{', payload) is not None

    items = []
    if is_atom:
        doc = ElementTree.fromstring(payload)

        for entry_el in doc.findall('{http://www.w3.org/2005/Atom}entry'):
            try:
                # Did we already see this post?
                atom_id = entry_el.find('{http://www.w3.org/2005/Atom}id').text

                # 35     $feed->id($self->{feed}->id);
                # 36     $feed->updated($self->{feed}->updated);
                # 37     $feed->title($self->{feed}->title);
                # 38     $feed->add_link({ href => $self->{feed}->link->href, rel => "self" });
                # 39 
                # 40     for my $entry (@entries) {
                # 41         $feed->add_entry($entry);
                # 42     }

                entry = {}
                entry['id'] = atom_id
                entry['xml_content'] = ElementTree.tostring(entry_el)
                entry['title'] = entry_el.find('{http://www.w3.org/2005/Atom}title').text

                content_el = entry_el.find('{http://www.w3.org/2005/Atom}content')
                if content_el is not None:
                    entry['content'] = content_el.text

                for link_el in entry_el.findall('{http://www.w3.org/2005/Atom}link'):
                    if link_el.get('rel', 'alternate') in ('alternate', 'href') and link_el.get('type', 'text/html') == 'text/html':
                        entry['permalink_url'] = link_el.get('href')
                    elif link_el.get('rel') == 'image':
                        entry['author_userpic'] = link_el.get('href')
                    elif link_el.get('rel') == 'self':
                        entry['self_url'] = link_el.get('href')

                published_el = entry_el.find('{http://www.w3.org/2005/Atom}published')
                if published_el is not None:
                    entry['published'] = iso8601.parse_date(published_el.text).astimezone(iso8601.UTC)

                updated_el = entry_el.find('{http://www.w3.org/2005/Atom}updated')
                if updated_el is not None:
                    entry['updated'] = iso8601.parse_date(updated_el.text).astimezone(iso8601.UTC)

                author_el = entry_el.find('{http://www.w3.org/2005/Atom}author')
                if author_el is not None:
                    for field in ('name', 'uri'):
                        field_el = author_el.find('{http://www.w3.org/2005/Atom}%s' % field)
                        if field_el is not None:
                            value = field_el.text
                        else:
                            value = ''
                        entry['author_%s' % field] = value

                source_el = entry_el.find('{http://www.w3.org/2005/Atom}source')
                if source_el is None:
                    source_el = doc
                if source_el is not None:
                    title_el = source_el.find('{http://www.w3.org/2005/Atom}title')
                    if title_el is not None:
                        entry['source_name'] = title_el.text
                    for link_el in source_el.findall('{http://www.w3.org/2005/Atom}link'):
                        if link_el.get('rel', 'alternate') == 'alternate' and link_el.get('type', 'text/html') == 'text/html':
                            entry['source_url'] = link_el.get('href')
                            break

                items.append(entry)

            except Exception, exc:
                log.exception(exc)  # but continue

    elif is_json:
        # handle json formatted content
        data = json.loads(payload)
        items = data['items']

    signals.feedsub_content.send(subscription=subscription, items=items, sender=receive)
    return HttpResponse('', status=200, content_type='text/plain')


def subscribe(request, sub_id):
    """Verify a subscription notice from TypePad."""
    challenge = request.GET['hub.challenge']
    verify_token = request.GET['hub.verify_token']

    try:
        sub = Subscription.objects.get(verify_token=verify_token)
        assert(sub.id == int(sub_id))
    except Subscription.DoesNotExist:
        return HttpResponseNotFound("Not expecting a subscription with verification token %r" % verify_token,
            content_type='text/plain')

    if not sub.verified:
        sub.verified = True
        sub.save()

    return HttpResponse(challenge, status=200, content_type='text/plain')
