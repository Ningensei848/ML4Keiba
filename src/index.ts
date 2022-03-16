import functions from '@google-cloud/functions-framework'
import type { HttpFunction } from '@google-cloud/functions-framework/build/src/functions'
import fetch from 'node-fetch'

export const proxyFetch: HttpFunction = async (req, res) => {
    const { query } = req
    const { url, encoding } = query

    if (typeof url !== 'string') {
        res.send('invalid parameter')
        return
    }

    const response = await fetch(url)

    if (typeof encoding === 'string') {
        res.set('Content-Type', `text/html; charset=${encoding}`)
        res.send(Buffer.from(await response.arrayBuffer()))
        return 1
    } else {
        const body = await response.text()
        res.send(body)
        return 1
    }
}

// Register an HTTP function with the Functions Framework that will be executed
// when you make an HTTP request to the deployed function's endpoint.
functions.http(process.env.ENTRYPOINT, proxyFetch)
