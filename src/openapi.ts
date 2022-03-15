import { default as path } from 'path'
import { default as util } from 'util'
import { default as childProcess } from 'child_process'
import { readFile, writeFile } from 'fs/promises'
import { dump } from 'js-yaml'

const exec = util.promisify(childProcess.exec)

// cf.https://cloud.google.com/api-gateway/docs/secure-traffic-console
const baseConfig = {
    swagger: '2.0',
    info: {
        title: 'scrap-proxy',
        description: 'ML4Keiba scraping API on API Gateway with a Google Cloud Functions backend',
        version: '0.0.0'
    },
    schemes: ['https'],
    produces: ['application/json'],
    // cf. https://cloud.google.com/endpoints/docs/openapi/restricting-api-access-with-api-keys
    securityDefinitions: {
        api_key: {
            type: 'apiKey',
            name: 'key',
            in: 'query'
        }
    }
}

const getFunctionNames = async (): Promise<string[]> => {
    const filepath = [process.cwd(), 'namelist.txt'].join(path.sep)
    const data = await readFile(filepath, 'utf-8')
    return data
        .split(/\n/)
        .map((l) => l.trim())
        .filter(Boolean)
}

const gcloudCommand =
    "gcloud run services list --region asia-northeast1 --project ml4keiba --format='value(name, status.url)'"

const getEndpoints = async () => {
    const { stdout } = await exec(gcloudCommand)
    const nameAndUrl = stdout.split(/\n/).map((line) => line.split(/\s/))
    return Object.fromEntries(nameAndUrl)
}

const makeConf = (name: string, endpoints: { [key: string]: string }) => {
    const conf = {
        get: {
            summary: `call function: ${name}`,
            operationId: name,
            'x-google-backend': {
                address: `${endpoints[name]}/${name}GET`
            },
            // cf. https://cloud.google.com/api-gateway/docs/secure-traffic-gcloud
            security: [{ api_key: [] }],
            responses: {
                '200': {
                    description: 'A successful response',
                    schema: {
                        type: 'string'
                    }
                }
            }
        }
    }

    return conf
}

const main = async () => {
    const functions = await getFunctionNames()
    const endpoints = await getEndpoints()
    const paths = Object.fromEntries(functions.map((name) => [`/${name}`, makeConf(name, endpoints)]))
    const yamlText = dump({ ...baseConfig, paths })
    await writeFile(`${process.cwd()}/openapi.yaml`, yamlText)
    console.log(yamlText)
}

await main()
