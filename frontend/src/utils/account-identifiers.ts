export type AccountIdentityLike = {
  accountId: string;
  email: string;
  displayName: string;
};

function identityKey(account: AccountIdentityLike): string {
  const candidate = account.email || account.displayName || account.accountId;
  return candidate.trim().toLowerCase();
}

export function buildDuplicateAccountIdSet<T extends AccountIdentityLike>(accounts: T[]): Set<string> {
  const groups = new Map<string, string[]>();

  for (const account of accounts) {
    const key = identityKey(account);
    const accountIds = groups.get(key);
    if (accountIds) {
      accountIds.push(account.accountId);
    } else {
      groups.set(key, [account.accountId]);
    }
  }

  const duplicates = new Set<string>();
  for (const accountIds of groups.values()) {
    if (accountIds.length <= 1) {
      continue;
    }
    for (const accountId of accountIds) {
      duplicates.add(accountId);
    }
  }

  return duplicates;
}

export function formatCompactAccountId(accountId: string, headChars = 8, tailChars = 6): string {
  const head = Math.max(1, headChars);
  const tail = Math.max(1, tailChars);
  if (accountId.length <= head + tail + 3) {
    return accountId;
  }
  return `${accountId.slice(0, head)}...${accountId.slice(-tail)}`;
}
