function get(url) {
    return fetch(url, {headers: {'Content-Type': 'application/json; charset=utf-8'}}
        ).then(resp => {
            if (resp.status >= 400) throw resp;
            return resp.json();
        });
}

function post(url, data) {
    return fetch(url,
        { method: 'POST',
          headers: {'Content-Type': 'application/json; charset=utf-8', 'Accept': 'application/json'},
          body: JSON.stringify(data),
        }).then(resp => {
            if (resp.status >= 400) throw resp;
            return resp.json();
        });
}

function del(url) {
    return fetch(url,
      {method: 'DELETE',
      }).then(resp => {
        if (resp.status >= 400) throw resp;
      });
}
