import asyncio
import os
import sys

# use local ichrome module
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
os.chdir("..")  # for reuse exiting user data dir


async def test_examples():
    from ichrome.async_utils import Chrome, logger, Tab, Tag
    from ichrome import ChromeDaemon
    import threading

    logger.setLevel('DEBUG')
    # Tab._log_all_recv = True
    port = 9222

    def async_run_chromed():

        def chrome_daemon():
            with ChromeDaemon(
                    host="127.0.0.1", port=port, max_deaths=1) as chromed:
                chromed.run_forever()

        threading.Thread(target=chrome_daemon, daemon=False).start()

    async_run_chromed()
    # ===================== Chrome Test Cases =====================
    chrome = Chrome()
    assert str(chrome) == '<Chrome(init): http://127.0.0.1:9222>'
    assert chrome.server == 'http://127.0.0.1:9222'
    try:
        await chrome.version
    except AttributeError as e:
        assert str(
            e
        ) == 'Chrome has not connected. `await chrome.connect()` before request.'
    # waiting chrome launching
    for _ in range(5):
        connected = await chrome.connect()
        if connected:
            break
        await asyncio.sleep(1)
    assert connected is True
    version = await chrome.version
    assert isinstance(version, dict) and 'Browser' in version
    ok = await chrome.check()
    assert ok is True
    ok = await chrome.ok
    assert ok is True
    resp = await chrome.get_server('json')
    assert isinstance(resp.json(), list)
    tabs1: Tab = await chrome.get_tabs()
    tabs2: Tab = await chrome.tabs
    assert tabs1 == tabs2
    tab0: Tab = tabs1[0]
    tab1: Tab = await chrome.new_tab()
    assert isinstance(tab1, Tab)
    await asyncio.sleep(1)
    await chrome.activate_tab(tab0)
    async with chrome.connect_tabs([tab0, tab1]):
        assert (await tab0.current_url) == 'about:blank'
        assert (await tab1.current_url) == 'about:blank'
    async with chrome.connect_tabs(tab0):
        assert await tab0.current_url == 'about:blank'
    await chrome.close_tab(tab1)
    # ===================== Tab Test Cases =====================
    tab: Tab = await chrome.new_tab()
    assert tab.ws is None
    async with tab():
        assert tab.ws
    assert tab.ws is None
    # also work: async with tab.connect():
    async with tab():
        assert tab.status == 'connected'
        assert tab.msg_id == tab.msg_id - 1
        assert await tab.refresh_tab_info()

        # watch the tabs switch
        await tab.activate_tab()
        await asyncio.sleep(.5)
        await tab0.activate_tab()
        await asyncio.sleep(.5)
        await tab.activate_tab()

        assert await tab.send('Network.enable') == {'id': 3, 'result': {}}
        await tab.clear_browser_cookies()
        assert len(await tab.get_cookies(urls='http://python.org')) == 0
        assert await tab.set_cookie(
            'test', 'test_value', url='http://python.org')
        assert await tab.set_cookie(
            'test2', 'test_value', url='http://python.org')
        assert len(await tab.get_cookies(urls='http://python.org')) == 2
        assert await tab.delete_cookies('test', url='http://python.org')
        assert len(await tab.get_cookies(urls='http://python.org')) == 1
        # get all Browser cookies
        assert len(await tab.get_all_cookies()) > 0
        # disable Network
        assert await tab.disable('Network')
        # set new url for this tab, timeout will stop loading
        assert await tab.set_url('http://python.org', timeout=2)
        # reload the page
        assert await tab.reload(timeout=2)
        # here should be press OK by human in 10 secs, get the returned result
        js_result = await tab.js('document.title', timeout=3)
        # {'id': 18, 'result': {'result': {'type': 'string', 'value': 'Welcome to Python.org'}}}
        assert 'result' in js_result
        # inject JS timeout return None
        assert (await tab.js('alert()', timeout=0.1)) is None
        # close the alert dialog
        await tab.enable('Page')
        await tab.send('Page.handleJavaScriptDialog', accept=True)
        # querySelectorAll with JS, return list of Tag object
        tag_list = await tab.querySelectorAll('#id-search-field')
        assert tag_list[0].tagName == 'input'
        # querySelectorAll with JS, index arg is Not None, return Tag or None
        one_tag = await tab.querySelectorAll('#id-search-field', index=0)
        assert isinstance(one_tag, Tag)
        # inject js url: vue.js
        # get window.Vue variable before injecting
        vue_obj = await tab.js('window.Vue')
        # {'id': 22, 'result': {'result': {'type': 'undefined'}}}
        assert 'undefined' in str(vue_obj)
        assert await tab.inject_js_url(
            'https://cdn.staticfile.org/vue/2.6.10/vue.min.js', timeout=3)
        vue_obj = await tab.js('window.Vue')
        # {'id': 23, 'result': {'result': {'type': 'function', 'className': 'Function', 'description': 'function wn(e){this._init(e)}', 'objectId': '{"injectedScriptId":1,"id":1}'}}}
        assert 'Function' in str(vue_obj)

        # update title
        await tab.js("document.title = 'Press about'")

        # wait_response by filter_function
        # {'method': 'Network.responseReceived', 'params': {'requestId': '1000003000.69', 'loaderId': 'D7814CD633EDF3E699523AF0C4E9DB2C', 'timestamp': 207483.974238, 'type': 'Script', 'response': {'url': 'https://www.python.org/static/js/libs/masonry.pkgd.min.js', 'status': 200, 'statusText': '', 'headers': {'date': 'Sat, 05 Oct 2019 08:18:34 GMT', 'via': '1.1 vegur, 1.1 varnish, 1.1 varnish', 'last-modified': 'Tue, 24 Sep 2019 18:31:03 GMT', 'server': 'nginx', 'age': '290358', 'etag': '"5d8a60e7-6643"', 'x-served-by': 'cache-iad2137-IAD, cache-tyo19928-TYO', 'x-cache': 'HIT, HIT', 'content-type': 'application/x-javascript', 'status': '200', 'cache-control': 'max-age=604800, public', 'accept-ranges': 'bytes', 'x-timer': 'S1570263515.866582,VS0,VE0', 'content-length': '26179', 'x-cache-hits': '1, 170'}, 'mimeType': 'application/x-javascript', 'connectionReused': False, 'connectionId': 0, 'remoteIPAddress': '151.101.108.223', 'remotePort': 443, 'fromDiskCache': True, 'fromServiceWorker': False, 'fromPrefetchCache': False, 'encodedDataLength': 0, 'timing': {'requestTime': 207482.696803, 'proxyStart': -1, 'proxyEnd': -1, 'dnsStart': -1, 'dnsEnd': -1, 'connectStart': -1, 'connectEnd': -1, 'sslStart': -1, 'sslEnd': -1, 'workerStart': -1, 'workerReady': -1, 'sendStart': 0.079, 'sendEnd': 0.079, 'pushStart': 0, 'pushEnd': 0, 'receiveHeadersEnd': 0.836}, 'protocol': 'h2', 'securityState': 'unknown'}, 'frameId': 'A2971702DE69F008914F18EAE6514DD5'}}
        async def cb(request):
            if request:
                await tab.wait_loading(5)
                ok = 'These are some' in (
                    await tab.get_response(request))['result']['body']
                logger.warning(
                    f'check wait_response callback, get_response {ok}')
                assert ok
            else:
                raise ValueError

        # listening response
        def filter_function(r):
            ok = r['params']['response'][
                'url'] == 'https://www.python.org/about/'
            return print('get response url:', r['params']['response']['url'],
                         ok) or ok

        task = asyncio.ensure_future(
            tab.wait_response(
                filter_function=filter_function,
                callback_function=cb,
                timeout=10),
            loop=tab.loop)
        await tab.click('#about>a')
        await task
        # click download link, without wait_loading.
        # request
        # {'method': 'Network.responseReceived', 'params': {'requestId': '2FAFC4FC410A6DEDE88553B1836C530B', 'loaderId': '2FAFC4FC410A6DEDE88553B1836C530B', 'timestamp': 212239.182469, 'type': 'Document', 'response': {'url': 'https://www.python.org/downloads/', 'status': 200, 'statusText': '', 'headers': {'status': '200', 'server': 'nginx', 'content-type': 'text/html; charset=utf-8', 'x-frame-options': 'DENY', 'cache-control': 'max-age=604800, public', 'via': '1.1 vegur\n1.1 varnish\n1.1 varnish', 'accept-ranges': 'bytes', 'date': 'Sat, 05 Oct 2019 10:51:48 GMT', 'age': '282488', 'x-served-by': 'cache-iad2139-IAD, cache-hnd18720-HND', 'x-cache': 'MISS, HIT', 'x-cache-hits': '0, 119', 'x-timer': 'S1570272708.444646,VS0,VE0', 'content-length': '113779'}, 'mimeType': 'text/html', 'connectionReused': False, 'connectionId': 0, 'remoteIPAddress': '123.23.54.43', 'remotePort': 443, 'fromDiskCache': True, 'fromServiceWorker': False, 'fromPrefetchCache': False, 'encodedDataLength': 0, 'timing': {'requestTime': 212239.179388, 'proxyStart': -1, 'proxyEnd': -1, 'dnsStart': -1, 'dnsEnd': -1, 'connectStart': -1, 'connectEnd': -1, 'sslStart': -1, 'sslEnd': -1, 'workerStart': -1, 'workerReady': -1, 'sendStart': 0.392, 'sendEnd': 0.392, 'pushStart': 0, 'pushEnd': 0, 'receiveHeadersEnd': 0.975}, 'protocol': 'h2', 'securityState': 'secure', 'securityDetails': {'protocol': 'TLS 1.2', 'keyExchange': 'ECDHE_RSA', 'keyExchangeGroup': 'X25519', 'cipher': 'AES_128_GCM', 'certificateId': 0, 'subjectName': 'www.python.org', 'sanList': ['www.python.org', 'docs.python.org', 'bugs.python.org', 'wiki.python.org', 'hg.python.org', 'mail.python.org', 'pypi.python.org', 'packaging.python.org', 'login.python.org', 'discuss.python.org', 'us.pycon.org', 'pypi.io', 'docs.pypi.io', 'pypi.org', 'docs.pypi.org', 'donate.pypi.org', 'devguide.python.org', 'www.bugs.python.org', 'python.org'], 'issuer': 'DigiCert SHA2 Extended Validation Server CA', 'validFrom': 1537228800, 'validTo': 1602676800, 'signedCertificateTimestampList': [], 'certificateTransparencyCompliance': 'unknown'}}, 'frameId': '882CFDEEA07EB00A5E7510ADD2A39F22'}}
        # response
        # {'id': 30, 'result': {'body': '<!doctype html>\n<!--[if lt IE 7]>   <html class="no-js ie6 lt-ie...', 'base64Encoded': False}}
        # test set_ua
        await tab.set_ua('Test UA')
        await tab.set_url('http://httpbin.org/get')
        html = await tab.get_html()
        assert '"User-Agent": "Test UA"' in html
        # test set_headers
        await tab.set_headers({'A': '1', 'B': '2'})
        await tab.set_url('http://httpbin.org/get')
        html = await tab.get_html()
        assert '"A": "1"' in html and '"B": "2"' in html
        # close tab
        await tab.close()
    await chrome.kill()
    sep = f'\n{"=" * 80}\n'
    logger.critical(f'{sep}Congratulations, all test cases passed.{sep}')


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_examples())
