// cf. https://qiita.com/mazxxxry/items/eb2036b28f75eb39333c
import { default as path } from 'path'
import { default as childProcess } from 'child_process'
import { readFile } from 'fs/promises'

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

const isFulfilled = <T>(input: PromiseSettledResult<T>): input is PromiseFulfilledResult<T> =>
    input.status === 'fulfilled'

const getFunctionNames = async (): Promise<string[]> => {
    const filepath = [process.cwd(), 'namelist.txt'].join(path.sep)
    const data = await readFile(filepath, 'utf-8')
    return data
        .split(/\n/)
        .map((l) => l.trim())
        .filter(Boolean)
}

const main = async () => {
    const functions = await getFunctionNames()

    // Promise<void> を要素とする配列を並列して解決させる
    const data = await Promise.allSettled(
        functions.map(
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
    )

    return data.filter(isFulfilled).map((r) => r.value)
}

await main()
