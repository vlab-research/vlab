pairup <- function (a) {
    N <- length(a)
    if (N %% 2 != 0) {
        stop('pairup needs an even-length vector')
    }
    out <- matrix(0, N/2, 2)
    for (i in 1:nrow(out)) {
        out[i,] <- a[1:2]
        a <- a[3:length(a)]
    }
    out
}

get_order <- function (m) {
    pca <- prcomp(scale(m))$x
    order(pca[, "PC1"])
}

pair <- function (di, blacklist) {
    s <- order(di)[2:length(di)]
    for (i in s) {
        if (!(i %in% blacklist)) {
            return(i)
        }
    }
}

pairem <- function (ma, or) {
    dists <- as.matrix(dist(scale(ma), method='euclidean'))
    pairs <- c()
    while(length(or) > 0) {
        i <- or[1]
        d <- dists[i, ]
        p <- pair(d, pairs)
        pairs <- append(pairs, c(i, p))
        or <- or[(or != p) & (or != i)]
    }
    pairs
}

flip <- function () {
    a <- rbinom(1, 1, 0.5)
    b <- ifelse(a == 0, 1, 0)
    c(a,b)
}

choose <- function(pairs) {
    # pairs is a vector where index 1 and index 2 are
    # a pair, same with index 3 and 4, etc...
    N <- length(pairs)
    out <- rep(0, N)
    for (i in seq(1, N, by=2)) {
        f <- flip()
        a <- pairs[i]
        b <- pairs[i+1]
        out[a] <- f[1]
        out[b] <- f[2]
    }
    out
}

get_balance <- function(dat, labels, print.level=0) {
    dat <- mutate(dat, a = labels)
    MatchBalance(a ~ kutchas + university + unemployed + malaria + malaria_now + population + cost_per_completion + cost_per_message + CTR + CPM + I(malaria**2) + I(malaria_now**2) + I(kutchas*population) + I(malaria*kutchas),
                 data=dat,
                 print.level=print.level)
}


above_threshes <- function (balance, threshes) {
    for (i in 1:length(threshes)) {
        thresh <- threshes[i]
        val <- balance$BeforeMatching[[i]]$tt$p.value
        if (val < thresh) {
            return(FALSE)
        }
    }
    TRUE
}

find_best_balance <- function (ma, iters, threshes) {
    selected_ma <- select(raw_ma, kutchas, university, malaria, malaria_now, population, cost_per_completion)
    or <- get_order(selected_ma)
    labels <- choose(pairem(selected_ma, or))

    best_balance <- NULL
    best_labels <- labels
    best_score <- 0.0

    for (i in 1:iters) {
        labels <- choose(pairem(selected_ma, or))
        balance <- get_balance(ma, labels)
        mi <- balance$BMsmallest.p.value
        malaria_p <- b$BeforeMatching[[4]]$tt$p.value
        if ((mi > best_score) & above_threshes(balance, threshes)) {
            best_score <- mi
            best_labels <- labels
            best_balance <- balance
        }
    }

    if (is.null(best_balance)) {
        stop('No suitable balance found!')
    }

    print(best_balance)
    best_labels
}

## raw_ma <- read_csv('outs/ma.csv')
## ma <- select(raw_ma, -disthash)
## bl5 <- find_best_balance(ma, 50, c(.6, .3, .3, .6, .75, .75, .3))
## write_csv(mutate(raw_ma, treatment=bl5), 'outs/ma-with-treatment.csv')
