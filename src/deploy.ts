// cf. https://qiita.com/mazxxxry/items/eb2036b28f75eb39333c
import { default as childProcess } from 'child_process'
import { readFile } from 'fs/promises'
import { default as path } from 'path'

// const command = (name: string) => `npm run deploy -name=${name} -entrypoint=${name}GET`

const command = (name: string) => `gcloud beta functions deploy ${name} \
--gen2 \
--quiet \
--trigger-http \
--entry-point ${name}GET \
--set-env-vars ENTRYPOINT=${name}GET \
--source . \
--runtime nodejs16 \
--region asia-northeast1 \
--memory=128MiB \
--timeout=15s
`

// const isFulfilled = <T>(input: PromiseSettledResult<T>): input is PromiseFulfilledResult<T> =>
//     input.status === 'fulfilled'

const getFunctionNames = async (): Promise<string[]> => {
    const filepath = [process.cwd(), 'namelist.txt'].join(path.sep)
    const data = await readFile(filepath, 'utf-8')
    return data
        .split(/\n/)
        .map((l) => l.trim())
        .filter(Boolean)
}

const getChunk = (functions: string[], size = 12) => {
    const promises = functions.map(
        (name) =>
            new Promise<void>((resolve, reject) => {
                try {
                    // 実行したコマンドの標準出力を表示
                    const spawn = childProcess.spawn(command(name), { shell: true })
                    spawn.stdout.on('data', (data) => {
                        console.log(data.toString())
                    })
                    spawn.stderr.on('data', (data) => {
                        console.error(data.toString())
                    })
                    spawn.on('close', (code) => {
                        console.log('CODE', code)
                    })
                    resolve()
                } catch (e) {
                    console.log(e)
                    reject(e)
                }
            })
    )

    const length = Math.ceil(promises.length / size)
    return [...Array(length)].map((_, i) => promises.slice(i * size, (i + 1) * size))
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

const chunkSize = 3

const main = async () => {
    const functions = await getFunctionNames()

    for (const chunk of getChunk(functions, chunkSize)) {
        // Promise<void> を要素とする配列を並列して解決させる
        await Promise.allSettled(chunk)
        await sleep(1000)
    }
}

await main()
