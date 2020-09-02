import * as argparse from 'argparse';
import * as fs from 'fs';
import * as netlog from './netlogtoqlog';


const parser = new argparse.ArgumentParser();

parser.add_argument('input');
parser.add_argument('output');

const cliArgs = parser.parse_args();

const { input, output } = cliArgs;

const json = JSON.parse(fs.readFileSync(input, 'utf-8'));
const qlog = netlog.default.convert(json);

fs.writeFileSync(output, JSON.stringify(qlog));