/**

#cron:20 10 * * *
 
 * 联想延保自动化脚本 
 * @description 变量lenovos: 手机号#密码#baseInfo，多号用&分隔
 * 使用说明:
 *   环境变量 lenovos 格式: 手机号#密码#baseInfo
 *   多账号用 & 分隔, 例如:
 *   lenovos=13800138000#mypassword#eyJhbGciOi...&13900139000#pass2#eyJhbGciOi...
 */
const axios = require('axios');
const CryptoJS = require('crypto-js');

// ============================================
// 全局变量
// ============================================
var $, users;

function get(options) {
  return axios({
    method: 'GET',
    url: options.url,
    headers: options.headers,
    timeout: options.timeout || 10000
  });
}

function post(options) {
  return axios({
    method: 'POST',
    url: options.url,
    data: options.body,
    headers: options.headers,
    timeout: options.timeout || 10000
  });
}

function AES_Encrypt(word) {
  var key = CryptoJS.enc.Utf8.parse('nihao_liu#zh*9@7');
  var iv = CryptoJS.enc.Utf8.parse('A*8@Stii_jin)*%6');
  var srcs = CryptoJS.enc.Utf8.parse(word);
  var encrypted = CryptoJS.AES.encrypt(srcs, key, {
    iv: iv,
    mode: CryptoJS.mode.CBC,
    padding: CryptoJS.pad.Pkcs7
  });
  return CryptoJS.enc.Hex.stringify(CryptoJS.enc.Base64.parse(encrypted.toString()));
}

class MainProgram {
  constructor(accountInfo, index) {
    var parts = accountInfo.split('#');
    this.phone = parts[0];
    this.password = parts[1];
    var baseInfo = parts[2];
    this.user = accountInfo;
    this.index = index;

    this.imei = JSON.parse(Buffer.from(baseInfo, 'base64').toString()).imei;

    this.headers = {
      'User-Agent': 'Apache-HttpClient/UNAVAILABLE (java 1.5)',
      'Connection': 'Keep-Alive',
      'Accept-Encoding': 'gzip,deflate',
      'X-Lenovo-APPID': '1',
      'BaseInfo': baseInfo,
      'unique': this.imei,
      'Authorization': 'Lenovosso null',
      'versionCode': '1000120',
      'aid': '17455550080789404',
      'sversion': '1647311400000',
      'Content-Type': 'text/json'
    };

    this.tgt = undefined;
    this.sessionid = undefined;
    this.uid = undefined;
  }

  log(msg) {
    console.log('账号[' + this.index + ']:' + msg);
  }

    async login() {
    var body = AES_Encrypt(JSON.stringify({
      'password': this.password,
      'shopId': '1',
      'sessionid': 'Lenovosso null',
      'time': Date.now(),
      'account': this.phone
    }));

    var response = await post({
      url: 'https://api.club.lenovo.cn/mapi/v2/lenovoid/password/login',
      body: body,
      headers: this.headers
    });

    var result = response.data;

    if (result.res.ret != 0) {
      throw new Error(result.res.msg);
    }

    this.tgt = result.res.tgt;
  }

  async get_authorization() {
    var encrypted = AES_Encrypt(JSON.stringify({
      'tgt': this.tgt,
      'sessionid': 'Lenovosso null',
      'time': Date.now()
    }));

    var url = 'https://api.club.lenovo.cn/mapi/v2/lenovoid/st?s=' + encrypted;

    var response = await get({
      url: url,
      headers: this.headers
    });

    var result = response.data;

    if (result.res.ret != 0) {
      throw new Error(result.res.msg);
    }

    this.sessionid = 'Lenovosso ' + result.res.data;
    this.headers['Authorization'] = this.sessionid;
  }

  async get_sessionID() {
    var encrypted = AES_Encrypt(JSON.stringify({
      'sessionid': this.sessionid,
      'time': Date.now()
    }));

    var url = 'https://api.club.lenovo.cn/users/getSessionID?s=' + encrypted;

    var response = await get({
      url: url,
      headers: this.headers
    });

    var result = response.data;

    if (result.status != 0) {
      throw new Error(decodeURIComponent(result.res.error_CN));
    }

    this.headers['token'] = result.res.token;
    this.uid = result.res.lenovoid;
    this.sessionid = 'Lenovo ' + result.res.sessionid;
    this.headers['Authorization'] = this.sessionid;
  }

  async signIn_status() {
    var encrypted = AES_Encrypt(JSON.stringify({
      'sessionid': this.sessionid,
      'time': Date.now()
    }));

    var url = 'https://api.club.lenovo.cn/common/signin/status?s=' + encrypted;

    var response = await get({
      url: url,
      headers: this.headers
    });

    var result = response.data;

    if (result.status != 0) {
      throw new Error(decodeURIComponent(result.res.error_CN));
    }

    if (result.res.is_signin) {
      throw new Error('用户已签到');
    }

    await this.signIn();
  }

  async signIn() {
    var body = AES_Encrypt(JSON.stringify({
      'uid': this.uid,
      'imei': this.imei,
      'source': '0',
      'sessionid': this.sessionid,
      'time': Date.now()
    }));

    var response = await post({
      url: 'https://api.club.lenovo.cn/signin/v2/add',
      body: body,
      headers: this.headers
    });

    var result = response.data;

    if (result.status != 0) {
      throw new Error(decodeURIComponent(result.res.error_CN));
    }

    this.log(result.res.rewardTips);
  }

  async doTask() {
    try {
      await this.login();
      await this.get_authorization();
      await this.get_sessionID();
      await this.signIn_status();
    } catch (error) {
      this.log(error.message);
    }
  }
}

async function _main() {
 
  await new Promise(resolve => setTimeout(resolve, 2000));
  for (var i = 0; i < users.length; i++) {
    if (users[i].trim()) {
      await new MainProgram(users[i], i + 1).doTask();
    }
  }
}

function main() {
  return _main.apply(this, arguments);
}

// ============================================
// 初始化 & 启动
// ============================================
users = (process.env['lenovos'] || '').split('&');

main();
